import json
import time

import numpy as np
import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState, ObsState
from tango import Database, DeviceProxy

from tests.settings import logger


@given(
    "a TANGO ecosystem with a set of devices deployed",
    target_fixture="device_list",
)
def device_list():
    db = Database()
    return db.get_device_exported("*")


@given(
    parsers.parse("a CentralNode device"),
    target_fixture="central_node",
)
def central_node():
    database = Database()
    instance_list = database.get_device_exported_for_class("CentralNodeLow")
    for instance in instance_list.value_string:
        return DeviceProxy(instance)
    instance_list = database.get_device_exported_for_class("CentralNodeMid")
    for instance in instance_list.value_string:
        return DeviceProxy(instance)


@when("I get the attribute InternalModel of the CentralNode device")
def internal_model(central_node):
    pytest.internal_model = central_node.internalModel


@when(parsers.parse("I call the command {command_name}"))
def call_command(central_node, command_name):
    try:
        pytest.command_result = central_node.command_inout(command_name)
    except Exception as ex:
        assert "CommandNotAllowed" in str(ex)
        pytest.command_result = "CommandNotAllowed"


@then("it correctly reports the failed and working devices")
def check_internal_model(device_list):
    json_model = json.loads(pytest.internal_model)
    logger.info(f"Json model is{json_model}")
    for dev in json_model["devices"]:
        running_dev = None
        for exported_dev in device_list.value_string:
            if exported_dev == dev["dev_name"]:
                running_dev = DeviceProxy(exported_dev)

        if running_dev is None:
            assert dev["unresponsive"] == "True"
            assert dev["exception"] != "None"
            continue
        assert "DevState." + str(running_dev.State()) == dev["state"]
        assert str(HealthState(running_dev.healthState)) == dev["healthState"]

        if "tm_subarray" in dev["dev_name"]:
            assert str(ObsState(running_dev.obsState)) == dev["obsState"]
            if running_dev.assignedResources is None:
                assert dev["resources"] == []
            else:
                assert (
                    np.asarray(running_dev.assignedResources)
                    == dev["resources"]
                )


@then(
    parsers.parse(
        "the command is queued and executed in less than {seconds} ss"
    )
)
def check_command(central_node, command_name, seconds, change_event_callbacks):
    if pytest.command_result == "CommandNotAllowed":
        return

    assert pytest.command_result[0][0] == ResultCode.QUEUED
    unique_id = pytest.command_result[1][0]

    central_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandsInQueue"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandsInQueue", (str(command_name),)
    )

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    start_time = time.time()
    executed = False
    while not executed:
        next_result = change_event_callbacks.assert_against_call(
            "longRunningCommandResult",
        )
        command_id, result = next_result["attribute_value"]

        if command_id != unique_id:
            next_result = change_event_callbacks.assert_against_call(
                "longRunningCommandResult",
                lookahead=2,
            )
            command_id, result = next_result["attribute_value"]
        assert command_id == unique_id
        assert int(result) == ResultCode.OK or int(result) == ResultCode.FAILED

        elapsed_time = time.time() - start_time
        if elapsed_time > float(seconds):
            pytest.fail("Timeout occurred while executing the test")
        else:
            executed = True

    change_event_callbacks.assert_change_event(
        "longRunningCommandsInQueue",
        None,
        lookahead=3,
    )


scenarios("../features/centralnode.feature")

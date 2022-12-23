import json

import numpy as np
import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState, ObsState
from ska_tmc_common.dev_factory import DevFactory
from tango import Database, DeviceProxy

from tests.settings import LOW_SUBARRAY_DEVICE, MID_SUBARRAY_DEVICE, logger


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
def call_command(central_node, command_name, json_factory):
    try:
        if command_name == "AssignResources":
            logger.info(f"central_node: {central_node.dev_name()}")
            if "ska_mid" in central_node.dev_name():
                assign_res_string = json_factory("command_AssignResources")
            else:
                assign_res_string = json_factory("command_assign_resource_low")
            pytest.command_result = central_node.command_inout(
                command_name, assign_res_string
            )
        elif command_name == "ReleaseResources":
            logger.info(f"central_node: {central_node.dev_name()}")
            if "ska_mid" in central_node.dev_name():
                release_res_string = json_factory("command_ReleaseResources")
            else:
                release_res_string = json_factory(
                    "command_release_resource_low"
                )
            pytest.command_result = central_node.command_inout(
                command_name, release_res_string
            )
        else:
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
        "the {command_name} command is executed successfully on lower level devices"
    )
)
def check_command(central_node, command_name, change_event_callbacks):

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

    change_event_callbacks.assert_change_event(
        "longRunningCommandsInQueue",
        None,
        lookahead=3,
    )

    if command_name == "AssignResources":
        # teardown subarray, setting ObsState = Empty
        dev_factory = DevFactory()
        if "ska_mid" in central_node.dev_name():
            tmc_subarray = dev_factory.get_device(MID_SUBARRAY_DEVICE)
        else:
            tmc_subarray = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
        tmc_subarray.SetDirectObsState(ObsState.EMPTY)


scenarios("../features/centralnode.feature")

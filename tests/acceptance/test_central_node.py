import json
import time

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenario, then, when
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState, ObsState
from tango import Database, DeviceProxy

from tests.settings import SLEEP_TIME, logger


@given(
    "a TANGO ecosystem with a set of devices deployed",
    target_fixture="device_list",
)
def device_list():
    db = Database()
    return db.get_device_exported("*")


@given(
    parsers.parse("a CentralNode device called <central_node_name>"),
    target_fixture="central_node",
)
def central_node(central_node_name):
    """a device called sys/tg_test/1."""
    return DeviceProxy(central_node_name)


@when("I get the attribute InternalModel of the CentralNode device")
def internal_model(central_node):
    pytest.internal_model = central_node.InternalModel


@when(parsers.parse("I call the command <command_name>"))
def call_command(central_node, command_name):
    try:
        pytest.command_result = central_node.command_inout(command_name)
    except Exception as ex:
        assert "CommandNotAllowed" in str(ex)
        pytest.command_result = "CommandNotAllowed"


@then("it correctly reports the failed and working devices")
def check_internal_model(device_list):
    json_model = json.loads(pytest.internal_model)
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

        if "subarray" in dev["dev_name"]:
            assert str(ObsState(running_dev.obsState)) == dev["obsState"]
            if running_dev.assignedResources is None:
                assert dev["resources"] == []
            else:
                assert (
                    np.asarray(running_dev.assignedResources)
                    == dev["resources"]
                )
            id = -1
            for s in running_dev.dev_name():
                if s.isdigit():
                    id = int(s)
            assert id == int(dev["id"])


@then(
    parsers.parse(
        "the command is queued and executed in less than {seconds} ss"
    )
)
def check_command(central_node, seconds):
    if pytest.command_result == "CommandNotAllowed":
        return

    assert pytest.command_result[0][0] == ResultCode.QUEUED
    unique_id = pytest.command_result[1][0]
    start_time = time.time()
    executed = False
    while not executed:
        for command in central_node.CommandExecuted:
            if command[0] == unique_id:
                logger.info("command result: %s", command)
                assert command[2] == str(ResultCode.OK) or command[2] == str(
                    ResultCode.FAILED
                )
                executed = True
        if executed:
            break
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > float(seconds):
            pytest.fail("Timeout occurred while executing the test")


@pytest.mark.post_deployment
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
@scenario(
    "../features/centralnode.feature",
    "Check internal model according to the TANGO ecosystem deployed",
)
def test_internal_model_mid(central_node_name):
    pass


@pytest.mark.post_deployment
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    ["central_node_name", "command_name"],
    [
        ("ska_mid/tm_central/central_node", "On"),
        ("ska_mid/tm_central/central_node", "Off"),
        ("ska_mid/tm_central/central_node", "Standby"),
        ("ska_mid/tm_central/central_node", "StartUpTelescope"),
        ("ska_mid/tm_central/central_node", "StandByTelescope"),
        ("ska_mid/tm_central/central_node", "TelescopeStandby"),
    ],
)
@scenario("../features/centralnode.feature", "Run Commands")
def test_run_commands_mid(central_node_name, command_name):
    pass


@pytest.mark.post_deployment
@pytest.mark.acceptance
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_low/tm_central/central_node")],
)
@scenario(
    "../features/centralnode.feature",
    "Monitor Telescope Components",
)
def test_internal_model_low(central_node_name):
    pass


@pytest.mark.post_deployment
@pytest.mark.acceptance
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    ["central_node_name", "command_name"],
    [
        ("ska_low/tm_central/central_node", "On"),
        ("ska_low/tm_central/central_node", "Off"),
        ("ska_low/tm_central/central_node", "Standby"),
        ("ska_low/tm_central/central_node", "StartUpTelescope"),
        ("ska_low/tm_central/central_node", "StandByTelescope"),
        ("ska_low/tm_central/central_node", "TelescopeStandby"),
    ],
)
@scenario(
    "../features/centralnode.feature",
    "Ability to run commands on central node",
)
def test_run_commands_low(central_node_name, command_name):
    pass

"""Test cases for centralnode command"""

# pylint:disable=redefined-outer-name
import json

import numpy as np
import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_control_model import AdminMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState, ObsState
from ska_tmc_common.dev_factory import DevFactory
from tango import Database, DeviceProxy

from tests.common_utils import wait_and_validate_device_attribute_value
from tests.settings import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_MLN_DEVICE,
    MID_CENTRAL_NODE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    check_subarray_availability,
    logger,
)


@given(
    "a TANGO ecosystem with a set of devices deployed",
    target_fixture="device_list",
)
def device_list():
    """Returns device list"""
    db = Database()
    return db.get_device_exported("*")


@given(
    parsers.parse("a CentralNode device"),
    target_fixture="central_node",
)
def central_node():
    """Central node device"""
    database = Database()
    instance_list = database.get_device_exported_for_class("LowTmcCentralNode")
    for instance in instance_list.value_string:
        return DeviceProxy(instance)
    instance_list = database.get_device_exported_for_class("MidTmcCentralNode")
    for instance in instance_list.value_string:
        dev_factory = DevFactory()
        assert wait_and_validate_device_attribute_value(
            dev_factory.get_device(MID_CENTRAL_NODE),
            "isDishVccConfigSet",
            True,
        ), "Timeout while waiting for validating attribute value"
        return DeviceProxy(instance)


@given("subsystem controllers are in adminMode ONLINE")
def set_admin_mode(central_node):
    """Set the adminMode for devices"""
    dev_name = central_node.dev_name()

    if "mid-tmc" in dev_name:
        csp_proxy = DeviceProxy(MID_CSP_MLN_DEVICE)
        sdp_proxy = DeviceProxy(MID_SDP_MLN_DEVICE)
        csp_proxy.SetCspControllerAdminMode(AdminMode.ONLINE)
        sdp_proxy.SetSdpControllerAdminMode(AdminMode.ONLINE)

    elif "low-tmc" in dev_name:
        csp_proxy = DeviceProxy(LOW_CSP_MLN_DEVICE)
        sdp_proxy = DeviceProxy(LOW_SDP_MLN_DEVICE)
        mccs_proxy = DeviceProxy(MCCS_MLN_DEVICE)
        csp_proxy.SetCspControllerAdminMode(AdminMode.ONLINE)
        sdp_proxy.SetSdpControllerAdminMode(AdminMode.ONLINE)
        mccs_proxy.SetMccsControllerAdminMode(AdminMode.ONLINE)


@when("I get the attribute InternalModel of the CentralNode device")
def internal_model(central_node):
    """Internal model method"""
    pytest.internal_model = central_node.internalModel


@when(parsers.parse("I call the command {command_name}"))
def call_command(central_node, command_name, json_factory):
    """Calls command on central node"""
    try:
        dev_factory = DevFactory()
        if command_name == "AssignResources":
            logger.info("central_node:%s", central_node.dev_name())
            if "mid-tmc" in central_node.dev_name():
                subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)
                green_mode = str(subarray_proxy.get_green_mode())
                assert "Futures" in green_mode
                subarray_proxy.SetisSubarrayAvailable(True)

                check_subarray_availability(
                    central_node, MID_SUBARRAY_DEVICE, True
                )

                assign_res_string = json_factory("command_AssignResources")

                pytest.command_result = central_node.command_inout(
                    command_name, assign_res_string
                )
            else:
                subarray_proxy = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
                subarray_proxy.SetisSubarrayAvailable(True)
                check_subarray_availability(
                    central_node, LOW_SUBARRAY_DEVICE, True
                )

                assign_res_string = json_factory("assign_resource_low")

                pytest.command_result = central_node.command_inout(
                    command_name, assign_res_string
                )
        elif command_name == "ReleaseResources":
            logger.info("central_node: %s", central_node.dev_name())
            if "mid-tmc" in central_node.dev_name():
                subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)
                subarray_proxy.SetisSubarrayAvailable(True)
                check_subarray_availability(
                    central_node, MID_SUBARRAY_DEVICE, True
                )
                subarray_proxy.SetDirectObsState(ObsState.IDLE)
                release_res_string = json_factory("command_ReleaseResources")
                pytest.command_result = central_node.command_inout(
                    command_name, release_res_string
                )
            else:
                subarray_proxy = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
                subarray_proxy.SetisSubarrayAvailable(True)
                check_subarray_availability(
                    central_node, LOW_SUBARRAY_DEVICE, True
                )
                subarray_proxy.SetDirectObsState(ObsState.IDLE)
                release_res_string = json_factory("release_resource_low")
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
    """checks internal model"""
    json_model = json.loads(pytest.internal_model)
    logger.info("Json model is %s", json_model)
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

        if "tmc/subarray/" in dev["dev_name"]:
            assert str(ObsState(running_dev.obsState)) == dev["obsState"]
            if running_dev.assignedResources == "{ }":
                assert dev["resources"] == ["{", " ", "}"]
            else:
                assert np.array_equal(
                    np.array(running_dev.assignedResources),
                    np.array(dev["resources"]),
                )


@then(
    parsers.parse(
        "the {command_name} command is executed successfully \
            on lower level devices"
    )
)
def check_command(central_node, command_name, change_event_callbacks):
    """Checks command for change event callback"""
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
        "longRunningCommandsInQueue",
        (command_name,),
        lookahead=4,
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
            lookahead=4,
        )
        command_id, result = next_result["attribute_value"]
    assert command_id == unique_id
    assert int(result) == ResultCode.OK or int(result) == ResultCode.FAILED

    change_event_callbacks.assert_change_event(
        "longRunningCommandsInQueue",
        None,
        lookahead=4,
    )

    if command_name == "AssignResources":
        # teardown subarray, setting ObsState = Empty
        dev_factory = DevFactory()
        if "mid-tmc" in central_node.dev_name():
            tmc_subarray = dev_factory.get_device(MID_SUBARRAY_DEVICE)
        else:
            tmc_subarray = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
        tmc_subarray.SetDirectObsState(ObsState.EMPTY)


scenarios("../features/centralnode.feature")

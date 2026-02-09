"""Integration tests for SetGlobalPointingModelCommand"""

import ast
import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import CENTRALNODE_MID
from tests.common_utils import wait_and_validate_device_attribute_value
from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    ERROR_PROPAGATION_DEFECT,
    MID_SUBARRAY_DEVICE,
    RESET_DEFECT,
    logger,
)


def set_gpm_command(tango_context, central_node_name, change_event_callbacks):
    """Test cases for SetGlobalPointing command"""

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    central_node.subscribe_event(
        "GlobalPointingModelStatus",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["GlobalPointingModelStatus"],
    )

    # Happy Scenario
    gpm_input = json.dumps(
        {
            "version": "1.0",
            "receptors": {
                "SKA001": ["Band_1"],
                "SKA036": ["Band_2"],
                "SKA063": ["Band_3"],
                "SKA100": ["Band_4", "Band_5a"],
            },
        }
    )

    result, unique_id = central_node.SetGlobalPointingModel(gpm_input)
    logger.info(
        "SetGlobalPointingModel Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("SetGlobalPointingModel")
    assert result[0] == ResultCode.QUEUED
    change_event_callbacks["GlobalPointingModelStatus"].assert_change_event(
        Anything,
        lookahead=4,
    )

    assertion_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=4,
    )

    result_data = json.loads(assertion_data["attribute_value"][1])

    command_completed = [0, "Command Completed"]
    output_data = result_data[1]
    gpm_input = json.loads(gpm_input)

    assert result_data[0] == int(ResultCode.OK)

    for receptor, bands in gpm_input["receptors"].items():
        lower_receptor = receptor.lower()
        assert lower_receptor in output_data

        for band in bands:
            assert band in output_data[lower_receptor]
            assert output_data[lower_receptor][band] == command_completed

    gpm_status = json.loads(central_node.GlobalPointingModelStatus)
    # Validate GPM status attribute
    for receptor, bands in gpm_input["receptors"].items():
        lower_receptor = receptor.lower()
        for band in bands:
            actual_version = gpm_status[lower_receptor].get(band)
            assert actual_version == gpm_input["version"]


def set_gpm_command_negative_scenarios(
    tango_context, central_node_name, change_event_callbacks
):
    """Test cases for SetGlobalPointing command"""

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    subarray_node = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    dln_100 = dev_factory.get_device("mid-tmc/leaf-node-dish/ska100")
    dln_100.SetDefective(ERROR_PROPAGATION_DEFECT)
    subarray_node.SetDirectassignedResources(("SKA001",))

    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    central_node.subscribe_event(
        "GlobalPointingModelStatus",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["GlobalPointingModelStatus"],
    )

    gpm_input = json.dumps(
        {
            "version": "1.0",
            "receptors": {
                "SKA001": ["Band_1"],
                "SKA036": ["Band_2"],
                "SKA093": ["Band_3"],
                "SKA100": ["Band_4"],
            },
        }
    )

    result, unique_id = central_node.SetGlobalPointingModel(gpm_input)
    logger.info(
        "SetGlobalPointingModel Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("SetGlobalPointingModel")
    assert result[0] == ResultCode.QUEUED
    change_event_callbacks["GlobalPointingModelStatus"].assert_change_event(
        Anything,
        lookahead=4,
    )

    assertion_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=4,
    )
    dln_100.SetDefective(RESET_DEFECT)
    result_data = json.loads(assertion_data["attribute_value"][1])
    gpm_status = json.loads(central_node.GlobalPointingModelStatus)
    assert result_data[0] == int(ResultCode.FAILED)
    result_data = ast.literal_eval(
        result_data[1].split("SetGPM failed on: ", 1)[1]
    )

    # Validate LRCR
    assert result_data["ska001"] == "ERROR: Dish is assigned to subarray"
    assert result_data["ska093"] == "ERROR: Dish is unreachable"
    assert result_data["ska100"]["Band_4"] == [
        3,
        "Exception occurred, command failed.",
    ]

    # Validate GlobalPointingModel Status
    # Status of SKA100, SKA093 and SKA001 will be
    # unchanged as no command execution
    # happened on it.
    subarray_node.SetDirectassignedResources([""])
    assert gpm_status["ska036"]["Band_2"] == "1.0"


def gpm_restart_scenarios(
    tango_context, central_node_name, change_event_callbacks
):
    """Test case to test GPM CN and DLN restart scenarios"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    subarray_node = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    dln_100 = dev_factory.get_device("mid-tmc/leaf-node-dish/ska100")
    subarray_node.SetDirectassignedResources(json.dumps(["SKA001"]))

    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    central_node.subscribe_event(
        "GlobalPointingModelStatus",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["GlobalPointingModelStatus"],
    )

    # Central Node restart scenario
    validate_lrcr_data = (
        '[0, {"ska100": {"Band_4": [0, "Command Completed"]}}]'
    )
    cn_device_server = tango.DeviceProxy("dserver/central_node_mid/01")
    cn_device_server.RestartServer()
    interface = "https://schema.skao.int/ska-mid-global-pointing-model/1.0"
    tm_data_sources = (
        "gitlab://gitlab.com/ska-telescope/ska-tmc/"
        + "ska-tmc-simulators?UNKNOWN#tmdata"
    )
    tm_file_path = "instrument/ska_mid1/global_pointing_model_data/"
    # Set Restart Simulation for SKA100
    gpm_data = {
        "ska100": [
            {
                "interface": interface,
                "tm_data_sources": tm_data_sources,
                "tm_data_filepath": tm_file_path + "gpm-ska100-Band_1.json",
            },
            {
                "interface": interface,
                "tm_data_sources": tm_data_sources,
                "tm_data_filepath": tm_file_path + "gpm-ska100-Band_2.json",
            },
            {
                "interface": interface,
                "tm_data_sources": tm_data_sources,
                "tm_data_filepath": tm_file_path + "gpm-ska100-Band_3.json",
            },
            {
                "interface": interface,
                "tm_data_sources": tm_data_sources,
                "tm_data_filepath": tm_file_path + "gpm-ska100-Band_4.json",
            },
            {
                "interface": interface,
                "tm_data_sources": tm_data_sources,
                "tm_data_filepath": tm_file_path + "gpm-ska100-Band_5a.json",
            },
            {
                "interface": interface,
                "tm_data_sources": tm_data_sources,
                "tm_data_filepath": tm_file_path + "gpm-ska100-Band_5b.json",
            },
        ]
    }

    for apm_input in gpm_data["ska100"]:
        dln_100.ApplyPointingModel(json.dumps(apm_input))

    wait_and_validate_device_attribute_value(
        central_node,
        "isDishVccConfigSet",
        True,
        timeout=300,
    )

    time.sleep(30)
    assertion_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (Anything, validate_lrcr_data),
        lookahead=10,
    )
    result_data = json.loads(assertion_data["attribute_value"][1])
    output_data = result_data[1]
    command_completed = [0, "Command Completed"]

    assert result_data[0] == int(ResultCode.OK)

    # As GPM invoked on band 4 only of SKA100
    assert output_data["ska100"]["Band_4"] == command_completed

    dish_ln_ds = tango.DeviceProxy("dserver/mocks/10")
    dish_ln_ds.RestartServer()

    # assert no SetGPM command executed as data is already set for SKA100
    with pytest.raises(AssertionError):
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (Anything, validate_lrcr_data),
            lookahead=10,
        )
    gpm_status = json.loads(central_node.GlobalPointingModelStatus)
    assert gpm_status["ska100"]["Band_4"] == "1.0.0"


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_set_gpm_command_negative_scenarios_all(
    tango_context,
    central_node_name,
    change_event_callbacks,
):
    """Test cases for set gpm command"""
    return set_gpm_command_negative_scenarios(
        tango_context,
        central_node_name,
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_set_gpm_command(
    tango_context,
    central_node_name,
    change_event_callbacks,
):
    """Test cases for set gpm command"""
    return set_gpm_command(
        tango_context,
        central_node_name,
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.restart_device_server
@pytest.mark.xfail(
    reason="Intermittentent failure due to device server restart"
)
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_set_gpm_command_restart_scenarios(
    tango_context,
    central_node_name,
    change_event_callbacks,
):
    """Test cases set gpm command"""
    return gpm_restart_scenarios(
        tango_context,
        central_node_name,
        change_event_callbacks,
    )

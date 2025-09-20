"""Integration tests for SetGlobalPointingModelCommand"""

import ast
import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import CENTRALNODE_MID
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
    change_event_callbacks.assert_change_event(
        "GlobalPointingModelStatus",
        Anything,
        lookahead=4,
    )

    assertion_data = change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
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
    change_event_callbacks.assert_change_event(
        "GlobalPointingModelStatus",
        Anything,
        lookahead=4,
    )

    assertion_data = change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], Anything),
        lookahead=4,
    )
    dln_100.SetDefective(RESET_DEFECT)
    result_data = json.loads(assertion_data["attribute_value"][1])
    gpm_status = json.loads(central_node.GlobalPointingModelStatus)
    assert result_data[0] == int(ResultCode.FAILED)
    result_data = ast.literal_eval(
        result_data[1].split("Command data: ", 1)[1]
    )

    # Validate LRCR
    assert result_data["ska001"] == "ERROR: Dish is assigned to subarray"
    assert result_data["ska093"] == "ERROR: Dish is unreachable"
    assert result_data["ska036"]["Band_2"] == [0, "Command Completed"]
    assert result_data["ska100"]["Band_4"] == [
        3,
        "Exception occurred, command failed.",
    ]

    # Validate GlobalPointingModel Status
    # Status of SKA100 and SKA001 will be unchanged as no command execution
    # happened on it.
    assert gpm_status["ska036"]["Band_2"] == "1.0"
    assert gpm_status["ska093"] == "ERROR: Dish is unreachable"


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.test1
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_set_gpm_command_negative_scenarios_all(
    tango_context,
    central_node_name,
    change_event_callbacks,
):
    """Test cases for Load_Dish_Config command"""
    return set_gpm_command_negative_scenarios(
        tango_context,
        central_node_name,
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.test11
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_set_gpm_command(
    tango_context,
    central_node_name,
    change_event_callbacks,
):
    """Test cases for Load_Dish_Config command"""
    return set_gpm_command(
        tango_context,
        central_node_name,
        change_event_callbacks,
    )

"""Test Module for SetStowMode command"""
import json
import re
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import CENTRALNODE_MID
from tests.integration.conftest import ensure_checked_devices
from tests.settings import ERROR_PROPAGATION_DEFECT, RESET_DEFECT, logger


def set_stow_mode_command(
    tango_context, central_node_name, change_event_callbacks
):
    """Test cases for SetStowMode command"""

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    dln1 = dev_factory.get_device("mid-tmc/leaf-node-dish/ska001")
    dln36 = dev_factory.get_device("mid-tmc/leaf-node-dish/ska036")
    dln36.SetDefective(RESET_DEFECT)
    dln1.SetDirectDishMode(5)  # set dish mode stow
    time.sleep(1)
    result, unique_id = central_node.SetStowMode('["ska001","ska036"]')
    logger.info(
        "SetStowMode Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("SetStowMode")
    assert result[0] == ResultCode.QUEUED

    assertion_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=4,
    )

    result_data = json.loads(assertion_data["attribute_value"][1])
    command_completed = [
        0,
        "SetStowMode succeeded on provided ['ska001', 'ska036'] dishes.",
    ]
    logger.info("Result Data 1: %s", result_data)
    assert command_completed == result_data

    # Negative Scenario: Dish is unreachable and Defect
    # Reset dish modes
    dln1.SetDirectDishMode(2)
    dln36.SetDirectDishMode(2)
    time.sleep(1)

    dln36.SetDefective(ERROR_PROPAGATION_DEFECT)
    time.sleep(0.5)

    result, unique_id = central_node.SetStowMode(
        '["ska001","ska036", "ska064"]'
    )
    logger.info(
        "SetStowMode Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )
    assert unique_id[0].endswith("SetStowMode")
    assert result[0] == ResultCode.QUEUED
    assertion_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=10,
    )
    result_data = json.loads(assertion_data["attribute_value"][1])
    logger.info("Result Data 2: %s", result_data)
    assert result_data[0] == ResultCode.FAILED
    assert "SetStowMode failed" in result_data[1]

    error_str = result_data[1]
    json_part = error_str.split(": ", 1)[1]
    match = re.search(r"\{.*\}", json_part)
    dict_str = match.group(0)
    data = json.loads(dict_str)
    err_msg1 = "Error in calling SetStowMode command on ska036 Dish Leaf Node"
    err_msg2 = "ERROR: Dish is unreachable"
    assert err_msg1 in data["ska036"]["result_code"]
    assert data["ska036"]["dish_mode"] == "STANDBY_LP"
    assert err_msg2 in data["ska064"]
    dln36.SetDefective(RESET_DEFECT)

    # Input argin as "ALL", with ALL as an argin execute on all dish leaf nodes
    # Reset dish modes
    dln1.SetDirectDishMode(2)
    dln36.SetDirectDishMode(2)
    time.sleep(1)
    result, unique_id = central_node.SetStowMode('["ALL"]')
    logger.info(
        "SetStowMode Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )
    assert unique_id[0].endswith("SetStowMode")
    assert result[0] == ResultCode.QUEUED
    assertion_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=4,
    )
    result_data = json.loads(assertion_data["attribute_value"][1])
    logger.info("Result Data 3: %s", result_data)
    assert result_data[0] == ResultCode.OK
    msg = "SetStowMode succeeded"
    assert msg in result_data[1]
    assert "ska001" in result_data[1]
    assert "ska036" in result_data[1]
    assert "ska063" in result_data[1]
    assert "ska100" in result_data[1]

    # Invalid Input
    result_code, message = central_node.SetStowMode('["ALL","ska036"]')
    assert ResultCode.REJECTED in result_code
    assert "Invalid input: Expected a list of dish IDs" in message[0]


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_set_stow_mode_command(
    tango_context,
    central_node_name,
    change_event_callbacks,
):
    """Test cases Set Stow mode command"""
    return set_stow_mode_command(
        tango_context,
        central_node_name,
        change_event_callbacks,
    )

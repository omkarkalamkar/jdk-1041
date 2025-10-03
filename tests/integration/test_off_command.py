"""Test cases for Off command"""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
    DISH_LEAF_NODE_1,
    DISH_LEAF_NODE_36,
    DISH_LEAF_NODE_63,
    DISH_LEAF_NODE_100,
    LOW_CSP_MASTER_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    MCCS_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_SDP_MASTER_DEVICE,
)
from tests.common_utils import wait_and_validate_device_attribute_value
from tests.integration.conftest import ensure_checked_devices
from tests.settings import DISH_DEFECT, RESET_DEFECT, logger


# pylint:disable=c-extension-no-member
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_off_command_mid(
    change_event_callbacks,
    set_mid_sdp_csp_mln_availability_for_aggregation,
    set_mid_sdp_csp_admin_modes,
    json_factory,
):
    """Test cases for Off command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    ensure_checked_devices(central_node)

    # 1. Ensure telescope is OFF before starting
    telescope_state = central_node.read_attribute("telescopeState").value
    if telescope_state == "ON":
        central_node.TelescopeOff()
        assert wait_and_validate_device_attribute_value(
            central_node, "telescopeState", "OFF", timeout=30
        )

    # 2. Load the Dish VCC configuration
    config_str = json_factory("command_load_dish_cfg")
    _, unique_id_cfg = central_node.LoadDishCfg(config_str)

    # Wait until LoadDishCfg completes
    # change_event_callbacks.assert_change_event(
    #     "longRunningCommandResult",
    #     (
    #         unique_id_cfg[0],
    #         json.dumps((int(ResultCode.OK), "Command Completed")),
    #     ),
    #     lookahead=6,
    # )
    # Assert LoadDishCfg completed (ignore exact payload)
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id_cfg[0], Anything),
        lookahead=10,
    )

    # 3. Validate Dish VCC config is COMPLETED
    assert wait_and_validate_device_attribute_value(
        central_node, "dishVccCommandStatus", "COMPLETED", timeout=30
    )

    result_on, unique_id_on = central_node.TelescopeOn()
    assert result_on[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id_on[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=4,
    )

    result_off, unique_id_off = central_node.TelescopeOff()
    assert result_off[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.OFF)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.OFF)

    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_1)
    dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )

    change_event_callbacks["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id_off[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=6,
    )

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.OFF, lookahead=12
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "device_name",
    [DISH_LEAF_NODE_1],
)
def test_off_command_dish_fail(
    device_name,
    change_event_callbacks,
):
    """Test TelescopeOff command failure on dish device"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)

    ensure_checked_devices(central_node)

    # config_str=json_factory("command_load_dish_cfg")
    # _, unique_id = central_node.LoadDishCfg(config_str)
    # change_event_callbacks.assert_change_event(
    #     "longRunningCommandResult",
    #     (
    #         unique_id[0],
    #         json.dumps((int(ResultCode.OK), "Command Completed")),
    #     ),
    #     lookahead=4,
    # )
    # Wait until Dish VCC config is set
    # assert wait_and_validate_device_attribute_value(
    #     central_node, "dishVccCommandStatus", "COMPLETED", timeout=300
    # )

    result_on, unique_id_on = central_node.TelescopeOn()
    assert result_on[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id_on[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=4,
    )

    tmc_dish = dev_factory.get_device(device_name)
    tmc_dish.SetDirectState(tango.DevState.ON)
    dish_defect = json.loads(DISH_DEFECT)
    dish_defect["error_message"] += device_name
    dish_defect = json.dumps(dish_defect)
    tmc_dish.SetDefective(dish_defect)

    result, unique_id = central_node.TelescopeOff()
    logger.info(
        "TelescopeOff Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("TelescopeOff")
    assert result[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.OFF)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.OFF)

    event_data = change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], Anything),
        lookahead=4,
    )

    exception_message = "Error in calling command for dish devices"

    assert exception_message in event_data["attribute_value"][1]
    assert device_name in event_data["attribute_value"][1]

    dish_leaf_node36 = dev_factory.get_device(DISH_LEAF_NODE_36)
    dish_leaf_node36.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )

    change_event_callbacks["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    dish_leaf_node63 = dev_factory.get_device(DISH_LEAF_NODE_63)
    dish_leaf_node63.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )

    change_event_callbacks["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    dish_leaf_node100 = dev_factory.get_device(DISH_LEAF_NODE_100)
    dish_leaf_node100.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )

    change_event_callbacks["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )
    tmc_dish.SetDefective(RESET_DEFECT)

    # Teardown
    result, unique_id = central_node.TelescopeOff()
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=8,
    )
    tmc_dish.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_off_command_low(
    change_event_callbacks,
    set_low_devices_availability_for_aggregation,
):
    """Test cases for off command for low"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)
    ensure_checked_devices(central_node)
    result_on, unique_id_on = central_node.TelescopeOn()
    result_off, unique_id_off = central_node.TelescopeOff()

    assert result_on[0] == ResultCode.QUEUED
    assert result_off[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id_on[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=3,
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id_off[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=3,
    )

    mccs_master = dev_factory.get_device(MCCS_MASTER_DEVICE)
    mccs_master.SetDirectState(tango.DevState.OFF)
    csp_master = dev_factory.get_device(LOW_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango._tango.DevState.OFF)

    csp_master.subscribe_event(
        "State",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["State"],
    )
    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )
    change_event_callbacks.assert_change_event(
        "State",
        tango._tango.DevState.OFF,
        lookahead=5,
    )

    sdp_master = dev_factory.get_device(LOW_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango._tango.DevState.OFF)

    sdp_master.subscribe_event(
        "State",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["State"],
    )
    change_event_callbacks.assert_change_event(
        "State",
        tango._tango.DevState.OFF,
        lookahead=3,
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.OFF, lookahead=4
    )

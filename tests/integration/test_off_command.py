"""Test cases for Off command"""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
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
from tests.settings import (
    DISH_DEFECT,
    RESET_DEFECT,
    check_dish_mode_event,
    check_exception,
    logger,
    telescope_on,
)


# pylint:disable=c-extension-no-member
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures(
    "set_mid_sdp_csp_mln_availability_for_aggregation",
    "set_mid_sdp_csp_admin_modes",
)
def test_off_command_mid(change_event_callbacks):
    """Test cases for Off command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)
    result_off, unique_id_off = central_node.TelescopeOff()
    assert result_off[0] == ResultCode.QUEUED

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.OFF)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.OFF)

    check_dish_mode_event(
        DISH_LEAF_NODE_1, DishMode.STANDBY_LP, change_event_callbacks
    )

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
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

    change_event_callbacks["telescopeState"].assert_change_event(
        tango.DevState.OFF, lookahead=12
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
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)
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

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.OFF)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.OFF)

    check_exception(
        change_event_callbacks,
        unique_id,
        device_name,
        "Error in calling command for dish devices",
    )
    for dish_ln in [DISH_LEAF_NODE_36, DISH_LEAF_NODE_63, DISH_LEAF_NODE_100]:
        check_dish_mode_event(
            dish_ln, DishMode.STANDBY_LP, change_event_callbacks
        )

    tmc_dish.SetDefective(RESET_DEFECT)

    # Teardown
    result, unique_id = central_node.TelescopeOff()
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=8,
    )
    tmc_dish.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_off_command_mid_all_dishes_standby_lp(
    change_event_callbacks,
):
    """Verify telescope goes OFF when all dishes are in STANDBY_LP and
    subsystems are OFF"""

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    ensure_checked_devices(central_node)
    # Subscribe command result
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    # Trigger OFF command
    result, unique_id = central_node.TelescopeOff()

    assert unique_id[0].endswith("TelescopeOff")
    assert result[0] == ResultCode.QUEUED

    # Set CSP and SDP to OFF (IMPORTANT)
    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.OFF)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.OFF)

    # Wait for command completion
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )

    # -------------------------------
    # Set ALL dishes to STANDBY_LP
    # -------------------------------
    dish1 = dev_factory.get_device(DISH_LEAF_NODE_1)
    dish2 = dev_factory.get_device(DISH_LEAF_NODE_36)
    dish3 = dev_factory.get_device(DISH_LEAF_NODE_63)

    dish1.SetDirectDishMode(DishMode.STANDBY_LP)
    dish2.SetDirectDishMode(DishMode.STANDBY_LP)
    dish3.SetDirectDishMode(DishMode.STANDBY_LP)

    # Subscribe telescope state
    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    # Verify telescope goes OFF
    change_event_callbacks["telescopeState"].assert_change_event(
        tango.DevState.OFF,
        lookahead=12,
    )
    assert central_node.telescopeState == tango.DevState.OFF


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_off_command_low(
    change_event_callbacks,
):
    """Test cases for off command for low"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)
    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    result_on, unique_id_on = central_node.TelescopeOn()
    result_off, unique_id_off = central_node.TelescopeOff()

    assert result_on[0] == ResultCode.QUEUED
    assert result_off[0] == ResultCode.QUEUED

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            unique_id_on[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=5,
    )
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            unique_id_off[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=5,
    )

    mccs_master = dev_factory.get_device(MCCS_MASTER_DEVICE)
    mccs_master.SetDirectState(tango.DevState.OFF)
    csp_master = dev_factory.get_device(LOW_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.OFF)

    csp_master.subscribe_event(
        "State",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["State"],
    )
    change_event_callbacks["State"].assert_change_event(
        tango.DevState.OFF,
        lookahead=5,
    )

    sdp_master = dev_factory.get_device(LOW_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.OFF)

    sdp_master.subscribe_event(
        "State",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["State"],
    )
    change_event_callbacks["State"].assert_change_event(
        tango.DevState.OFF,
        lookahead=3,
    )
    assert wait_and_validate_device_attribute_value(
        central_node, "telescopeState", tango.DevState.OFF
    )

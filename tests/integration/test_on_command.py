"""Test cases for ON command"""

import json

import pytest
import tango
from ska_control_model import HealthState
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
from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    DISH_DEFECT,
    RESET_DEFECT,
    check_dish_mode_event,
    check_exception,
    telescope_off,
    telescope_on,
)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_on_command_mid(change_event_callbacks):
    """Test cases for ON command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    assert central_node.HealthState == HealthState.OK
    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    result, unique_id = central_node.TelescopeOn()

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.ON)

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    check_dish_mode_event(
        DISH_LEAF_NODE_1, DishMode.STANDBY_FP, change_event_callbacks
    )

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks["telescopeState"].assert_change_event(
        tango.DevState.ON, lookahead=12
    )
    assert central_node.telescopeState == tango.DevState.ON
    # Teardown
    telescope_off(central_node, change_event_callbacks)


# @pytest.mark.post_deployment
# @pytest.mark.SKA_mid
# @pytest.mark.parametrize(
#     "device_name",
#     [DISH_LEAF_NODE_1],
# )
# def test_on_command_dish_fail(
#     device_name,
#     change_event_callbacks,
# ):
#     """Test TelescopeOn command failure on dish device"""
#     dev_factory = DevFactory()
#     central_node = dev_factory.get_device(CENTRALNODE_MID)

#     ensure_checked_devices(central_node)

#     tmc_dish = dev_factory.get_device(device_name)
#     dish_defect = json.loads(DISH_DEFECT)
#     dish_defect["error_message"] += device_name
#     dish_defect = json.dumps(dish_defect)
#     tmc_dish.SetDefective(dish_defect)
#     central_node.subscribe_event(
#         "longRunningCommandResult",
#         tango.EventType.CHANGE_EVENT,
#         change_event_callbacks["longRunningCommandResult"],
#     )
#     result_on, unique_id = central_node.TelescopeOn()
#     assert result_on[0] == ResultCode.QUEUED
#     assert unique_id[0].endswith("TelescopeOn")

#     csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
#     csp_master.SetDirectState(tango.DevState.ON)

#     sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
#     sdp_master.SetDirectState(tango.DevState.ON)

#     # Refactored CommandExecutor formats dish failures as:
#     # "Error occurred for device <trl>: Unexpected result code
#     # for SetStandbyFPMode command: 3"
#     check_exception(
#         change_event_callbacks,
#         unique_id,
#         device_name,
#         f"Error occurred for device {device_name}",
#     )

#     for dish_ln in [DISH_LEAF_NODE_36, DISH_LEAF_NODE_63,
# DISH_LEAF_NODE_100]:
#         check_dish_mode_event(
#             dish_ln, DishMode.STANDBY_FP, change_event_callbacks
#         )

#     tmc_dish.SetDefective(RESET_DEFECT)

#     # Teardown
#     telescope_off(central_node, change_event_callbacks)

#     tmc_dish.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "device_name",
    [DISH_LEAF_NODE_1],
)
def test_on_command_dish_fail(
    device_name,
    change_event_callbacks,
):
    """Test TelescopeOn command failure on dish device"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)

    ensure_checked_devices(central_node)

    tmc_dish = dev_factory.get_device(device_name)
    dish_defect = json.loads(DISH_DEFECT)
    dish_defect["error_message"] += device_name
    dish_defect = json.dumps(dish_defect)
    tmc_dish.SetDefective(dish_defect)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    result_on, unique_id = central_node.TelescopeOn()
    assert result_on[0] == ResultCode.QUEUED
    assert unique_id[0].endswith("TelescopeOn")

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.ON)

    check_exception(
        change_event_callbacks,
        unique_id,
        device_name,
        "Error in calling command for dish devices",
    )

    for dish_ln in [DISH_LEAF_NODE_36, DISH_LEAF_NODE_63, DISH_LEAF_NODE_100]:
        check_dish_mode_event(
            dish_ln, DishMode.STANDBY_FP, change_event_callbacks
        )

    tmc_dish.SetDefective(RESET_DEFECT)

    # Teardown
    telescope_off(central_node, change_event_callbacks)

    tmc_dish.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_on_command_low(
    change_event_callbacks,
):
    """Test cases for ON command for low"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)
    assert central_node.HealthState == HealthState.OK
    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    mccs_master = dev_factory.get_device(MCCS_MASTER_DEVICE)
    mccs_master.SetDirectState(tango.DevState.ON)

    csp_master = dev_factory.get_device(LOW_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device(LOW_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.ON)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks["telescopeState"].assert_change_event(
        tango.DevState.ON, lookahead=4
    )
    assert central_node.telescopeState == tango.DevState.ON
    # Teardown
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "dish_modes, expected_state",
    [
        # Partial availability (degraded scenario)
        (
            {
                "dish1": DishMode.STANDBY_FP,
                "dish2": DishMode.STANDBY_LP,
                "dish3": DishMode.SHUTDOWN,
            },
            tango.DevState.ON,
        ),
        # All usable (healthy scenario)
        (
            {
                "dish1": DishMode.STANDBY_FP,
                "dish2": DishMode.STANDBY_FP,
                "dish3": DishMode.STANDBY_FP,
            },
            tango.DevState.ON,
        ),  # Mixed modes but still usable (healthy scenario)
        (
            {
                "dish1": DishMode.STANDBY_FP,
                "dish2": DishMode.OPERATE,
                "dish3": DishMode.CONFIG,
            },
            tango.DevState.ON,
        ),
        (
            {
                "dish1": DishMode.STANDBY_LP,
                "dish2": DishMode.OPERATE,
                "dish3": DishMode.SHUTDOWN,
            },
            tango.DevState.ON,
        ),
        (
            {
                "dish1": DishMode.STANDBY_LP,
                "dish2": DishMode.SHUTDOWN,
                "dish3": DishMode.CONFIG,
            },
            tango.DevState.ON,
        ),
    ],
)
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_on_command_mid_dish_availability_parametrized(
    dish_modes,
    expected_state,
    change_event_callbacks,
):
    """Test ON command with different dish availability scenarios"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)

    ensure_checked_devices(central_node)

    assert central_node.HealthState == HealthState.OK

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    result, unique_id = central_node.TelescopeOn()

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    # CSP + SDP ON
    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.ON)

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    # -------------------------------
    # Dish configuration (parametrized)
    # -------------------------------
    dish1 = dev_factory.get_device(DISH_LEAF_NODE_1)
    dish2 = dev_factory.get_device(DISH_LEAF_NODE_36)
    dish3 = dev_factory.get_device(DISH_LEAF_NODE_63)

    dish1.SetDirectDishMode(dish_modes["dish1"])
    dish2.SetDirectDishMode(dish_modes["dish2"])
    dish3.SetDirectDishMode(dish_modes["dish3"])

    # Subscribe telescope state
    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks["telescopeState"].assert_change_event(
        expected_state,
        lookahead=12,
    )

    assert central_node.telescopeState == expected_state
    # -------------------------------
    # Teardown
    # -------------------------------
    telescope_off(central_node, change_event_callbacks)

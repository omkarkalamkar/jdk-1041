"""Test cases for ON command"""

import json

import pytest
import tango
from ska_control_model import HealthState
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
from tests.settings import DISH_DEFECT, RESET_DEFECT


# pylint:disable=c-extension-no-member
# this linting warning is suppressed cause its not able to recognise
# tango._tango.Devstate which is c-extension member
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_on_command_mid(
    change_event_callbacks,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
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

    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_1)
    dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )
    change_event_callbacks["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
    )

    assert central_node.telescopeState == tango.DevState.ON
    # Teardown
    result, unique_id = central_node.TelescopeOff()
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=8,
    )


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

    event_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
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
        (DishMode.STANDBY_FP),
        lookahead=2,
    )

    dish_leaf_node63 = dev_factory.get_device(DISH_LEAF_NODE_63)
    dish_leaf_node63.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )

    change_event_callbacks["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
    )

    dish_leaf_node100 = dev_factory.get_device(DISH_LEAF_NODE_100)
    dish_leaf_node100.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )

    change_event_callbacks["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
    )

    tmc_dish.SetDefective(RESET_DEFECT)

    # Teardown
    _, unique_id = central_node.TelescopeOff()
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=8,
    )
    tmc_dish.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_on_command_low(
    change_event_callbacks,
    set_low_devices_availability_for_aggregation,
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
    result, unique_id = central_node.TelescopeOn()

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    mccs_master = dev_factory.get_device(MCCS_MASTER_DEVICE)
    mccs_master.SetDirectState(tango.DevState.ON)

    csp_master = dev_factory.get_device(LOW_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device(LOW_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.ON)

    assert wait_and_validate_device_attribute_value(
        central_node, "telescopeState", tango.DevState.ON
    )

    # Teardown
    result, unique_id = central_node.TelescopeOff()
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

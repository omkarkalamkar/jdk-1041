"""Test cases for standby command"""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode
from tango import DevState

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
    DISH_LEAF_NODE_1,
    LOW_CSP_MASTER_DEVICE,
    MCCS_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
)
from tests.common_utils import wait_and_validate_device_attribute_value
from tests.integration.conftest import ensure_checked_devices
from tests.settings import logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_standby_command_mid(
    change_event_callbacks,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test standby command for mid"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    result, unique_id = central_node.TelescopeOn()
    # Check whether the command ResultCode is OK

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=8,
    )
    logger.info(
        "longRunningCommandResult: %s",
        str(central_node.longRunningCommandResult),
    )

    result, unique_id = central_node.TelescopeStandby()
    logger.info("Result is: %s", str(result))
    logger.info("Unique id: %s", unique_id)

    # Check whether the command is QUEUED
    assert unique_id[0].endswith("TelescopeStandby")
    assert result[0] == ResultCode.QUEUED

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(DevState.STANDBY)

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

    # Check whether the command ResultCode is OK
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    logger.info(
        "longRunningCommandResult: %s",
        str(central_node.longRunningCommandResult),
    )

    logger.info("telescopeState: %s", str(central_node.telescopeState))

    assert central_node.telescopeState == DevState.STANDBY


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_standby_command_low(
    change_event_callbacks,
    set_low_devices_availability_for_aggregation,
):
    """Test standby command for low"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)
    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    result, unique_id = central_node.TelescopeOn()
    # Check whether the command ResultCode is OK

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=8,
    )
    logger.info(
        "longRunningCommandResult: %s",
        str(central_node.longRunningCommandResult),
    )

    result, unique_id = central_node.TelescopeStandby()
    logger.info("Result is: %s. Unique ID is %s", str(result), unique_id)

    # Check whether the command is QUEUED
    assert unique_id[0].endswith("TelescopeStandby")
    assert result[0] == ResultCode.QUEUED

    # Check whether the command ResultCode is OK
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=3,
    )
    logger.info(
        "longRunningCommandResult: %s",
        str(central_node.longRunningCommandResult),
    )

    mccs_master = dev_factory.get_device(MCCS_MASTER_DEVICE)
    mccs_master.SetDirectState(DevState.STANDBY)

    csp_master = dev_factory.get_device(LOW_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(DevState.STANDBY)

    assert wait_and_validate_device_attribute_value(
        central_node, "telescopeState", DevState.STANDBY
    )

    assert central_node.telescopeState == DevState.STANDBY

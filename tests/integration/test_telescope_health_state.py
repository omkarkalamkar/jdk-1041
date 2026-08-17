"""Test telescope health state"""

import time

import pytest
import tango
from ska_tango_base.control_model import AdminMode, HealthState
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
    DISH_LEAF_NODE_1,
    DISH_LEAF_NODE_36,
    DISH_LEAF_NODE_63,
    DISH_LEAF_NODE_77,
    DISH_LEAF_NODE_099,
    DISH_LEAF_NODE_100,
    DISH_LEAF_NODE_500,
    DISH_LEAF_NODE_999,
    DISH_LEAF_NODE_MKT,
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MCCS_MLN_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
)
from tests.common_utils import wait_and_validate_device_attribute_value
from tests.integration.conftest import ensure_checked_devices
from tests.settings import logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_health_state_mid(change_event_callbacks):
    """test telescope health state mid"""

    dev_factory = DevFactory()
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_mln.SetSdpControllerAdminMode(AdminMode.ONLINE)
    csp_mln.SetCspControllerAdminMode(AdminMode.ONLINE)
    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "telescopeHealthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeHealthState"],
    )
    sdp_master.subscribe_event(
        "healthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["healthState"],
    )

    sdp_master.SetDirectHealthState(HealthState.DEGRADED)
    change_event_callbacks["healthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=8
    )
    time.sleep(0.3)
    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=8
    )

    assert central_node.telescopeHealthState == HealthState.DEGRADED

    # tear down
    sdp_master.SetDirectHealthState(HealthState.OK)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.OK, lookahead=4
    )
    logger.info("telescopeHealthState %s", central_node.telescopeHealthState)
    time.sleep(0.3)
    logger.info("telescopeHealthState %s", central_node.telescopeHealthState)
    assert central_node.telescopeHealthState == HealthState.OK


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_telescope_health_state_low(change_event_callbacks):
    """test telescope health state low"""

    dev_factory = DevFactory()
    mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    central_node = dev_factory.get_device(CENTRALNODE_LOW)
    mccs_mln.SetMccsControllerAdminMode(AdminMode.ONLINE)
    sdp_mln.SetSdpControllerAdminMode(AdminMode.ONLINE)
    csp_mln.SetCspControllerAdminMode(AdminMode.ONLINE)
    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "telescopeHealthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeHealthState"],
    )

    sdp_master = dev_factory.get_device(LOW_SDP_MASTER_DEVICE)
    sdp_master.SetDirectHealthState(HealthState.DEGRADED)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=8
    )

    time.sleep(0.3)
    assert central_node.telescopeHealthState == HealthState.DEGRADED

    # tear down
    sdp_master.SetDirectHealthState(HealthState.OK)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.OK, lookahead=4
    )
    logger.info("telescopeHealthState %s", central_node.telescopeHealthState)
    time.sleep(0.1)
    logger.info("telescopeHealthState %s", central_node.telescopeHealthState)
    assert central_node.telescopeHealthState == HealthState.OK


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_command_timeout():
    """test telescope health state mid"""

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    central_node.commandTimeOut = 200
    logger.info("Command Timeout after %s", central_node.commandTimeOut)
    assert central_node.commandTimeOut == 200


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_health_state_single_dish_degraded_state(
    change_event_callbacks,
):
    """Test CN aggregates healthState reported by Dish Leaf Node"""

    dev_factory = DevFactory()

    central_node = dev_factory.get_device(CENTRALNODE_MID)
    dish_ln = dev_factory.get_device(DISH_LEAF_NODE_1)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln.SetSdpControllerAdminMode(AdminMode.ONLINE)
    csp_mln.SetCspControllerAdminMode(AdminMode.ONLINE)

    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "telescopeHealthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeHealthState"],
    )

    dish_ln.subscribe_event(
        "healthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["healthState"],
    )

    # Dish reports DEGRADED
    dish_ln.SetDirectHealthState(HealthState.DEGRADED)

    change_event_callbacks["healthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=8
    )

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=8
    )

    assert central_node.telescopeHealthState == HealthState.DEGRADED

    # Tear down: Dish reports OK
    dish_ln.SetDirectHealthState(HealthState.OK)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.OK, lookahead=8
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_health_state_handles_multi_dish_failure(
    change_event_callbacks,
):
    """Test CN aggregates healthState reported by Dish Leaf Node"""

    dev_factory = DevFactory()

    central_node = dev_factory.get_device(CENTRALNODE_MID)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln.SetSdpControllerAdminMode(AdminMode.ONLINE)
    csp_mln.SetCspControllerAdminMode(AdminMode.ONLINE)
    dish_lns = [
        DISH_LEAF_NODE_1,
        DISH_LEAF_NODE_36,
        DISH_LEAF_NODE_63,
        DISH_LEAF_NODE_77,
        DISH_LEAF_NODE_100,
        DISH_LEAF_NODE_099,
        DISH_LEAF_NODE_500,
        DISH_LEAF_NODE_999,
        DISH_LEAF_NODE_MKT,
    ]

    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "telescopeHealthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeHealthState"],
    )

    for dish_ln in dish_lns:
        dish_ln_proxy = dev_factory.get_device(dish_ln)
        dish_ln_proxy.SetDirectHealthState(HealthState.FAILED)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.FAILED, lookahead=8
    )

    #  Dish1 reports OK
    dish_ln1_proxy = dev_factory.get_device(dish_lns[0])
    dish_ln1_proxy.SetDirectHealthState(HealthState.OK)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=8
    )
    # Tear down: Dish reports OK
    for dish_ln in dish_lns:
        dish_ln_proxy = dev_factory.get_device(dish_ln)
        dish_ln_proxy.SetDirectHealthState(HealthState.OK)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.OK, lookahead=8
    )

    assert wait_and_validate_device_attribute_value(
        central_node,
        "telescopeHealthState",
        HealthState.OK,
    )

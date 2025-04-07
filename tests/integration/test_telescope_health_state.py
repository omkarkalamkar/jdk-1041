"""Test telescope health state"""
import time

import pytest
import tango
from ska_tango_base.control_model import HealthState
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
    LOW_SDP_MASTER_DEVICE,
    MID_SDP_MASTER_DEVICE,
)
from tests.integration.conftest import ensure_checked_devices
from tests.settings import logger


@pytest.mark.aki
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_health_state_mid(tango_context, change_event_callbacks):
    """test telescope health state mid"""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)

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
        HealthState.DEGRADED, lookahead=2
    )

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=2
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
def test_telescope_health_state_low(tango_context, change_event_callbacks):
    """test telescope health state low"""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "telescopeHealthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeHealthState"],
    )

    sdp_master = dev_factory.get_device(LOW_SDP_MASTER_DEVICE)
    sdp_master.SetDirectHealthState(HealthState.DEGRADED)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=2
    )
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

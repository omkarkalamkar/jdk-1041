import time

import pytest
import tango
from ska_tango_base.control_model import HealthState
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.common import devices_to_load  # noqa F401
from tests.integration.common import ensure_checked_devices
from tests.settings import logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_health_state_mid(tango_context, change_event_callbacks):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "telescopeHealthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeHealthState"],
    )

    sdp_master = dev_factory.get_device("mid-sdp/control/0")
    sdp_master.SetDirectHealthState(HealthState.DEGRADED)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=2
    )

    assert central_node.telescopeHealthState == HealthState.DEGRADED

    # tear down
    sdp_master.SetDirectHealthState(HealthState.OK)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.OK, lookahead=2
    )
    logger.info("telescopeHealthState %s", central_node.telescopeHealthState)
    time.sleep(0.1)
    logger.info("telescopeHealthState %s", central_node.telescopeHealthState)
    assert central_node.telescopeHealthState == HealthState.OK



@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_telescope_health_state_low(tango_context, change_event_callbacks):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_low/tm_central/central_node")

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "telescopeHealthState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeHealthState"],
    )

    sdp_master = dev_factory.get_device("low-sdp/control/0")
    sdp_master.SetDirectHealthState(HealthState.DEGRADED)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.DEGRADED, lookahead=2
    )
    assert central_node.telescopeHealthState == HealthState.DEGRADED

    # tear down
    sdp_master.SetDirectHealthState(HealthState.OK)

    change_event_callbacks["telescopeHealthState"].assert_change_event(
        HealthState.OK, lookahead=2
    )
    logger.info("telescopeHealthState %s", central_node.telescopeHealthState)
    time.sleep(0.1)
    logger.info("telescopeHealthState %s", central_node.telescopeHealthState)
    assert central_node.telescopeHealthState == HealthState.OK

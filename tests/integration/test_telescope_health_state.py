import pytest
import tango
from ska_tango_base.control_model import HealthState

from ska_tmc_centralnode.dev_factory import DevFactory
from tests.integration.common import devices_to_load  # noqa F401
from tests.integration.common import (
    assert_event_arrived,
    ensure_checked_devices,
)
from tests.settings import logger


def telescope_health_state(tango_context, centralnode_name):
    # import debugpy; debugpy.debug_this_thread()
    pytest.event_arrived = False

    def event_callback(evt):
        assert not evt.err
        logger.info(evt.attr_value.value)
        if evt.attr_value.value == HealthState.DEGRADED:
            pytest.event_arrived = True

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(centralnode_name)

    event_id = central_node.subscribe_event(
        "telescopehealthstate",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    ensure_checked_devices(central_node)

    sdp_master = dev_factory.get_device("mid_sdp/elt/master")
    sdp_master.SetDirectHealthState(HealthState.DEGRADED)
    mccs_master = dev_factory.get_device("low-mccs/control/control")
    mccs_master.SetDirectHealthState(HealthState.DEGRADED)

    assert_event_arrived()

    assert central_node.telescopehealthstate == HealthState.DEGRADED

    central_node.unsubscribe_event(event_id)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_health_state_mid(tango_context):
    telescope_health_state(tango_context, "ska_mid/tm_central/central_node")


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_telescope_health_state_low(tango_context):
    telescope_health_state(tango_context, "ska_low/tm_central/central_node")

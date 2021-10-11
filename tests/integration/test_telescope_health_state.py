import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from tango import DevState

from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.integration.common import devices_to_load, ensure_checked_devices
from tests.settings import SLEEP_TIME, TIMEOUT, logger


@pytest.mark.post_deployment
def test_telescope_health_state(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    pytest.event_arrived = False

    def event_callback(evt):
        assert not evt.err
        logger.info(evt.attr_value.value)
        if evt.attr_value.value == HealthState.DEGRADED:
            pytest.event_arrived = True

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "telescopeHealthState",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    ensure_checked_devices(central_node)

    sdp_master = dev_factory.get_device("mid_sdp/elt/master")
    sdp_master.SetDirectHealthState(HealthState.DEGRADED)

    start_time = time.time()
    while not pytest.event_arrived:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.event_arrived

    assert central_node.telescopeHealthState == HealthState.DEGRADED

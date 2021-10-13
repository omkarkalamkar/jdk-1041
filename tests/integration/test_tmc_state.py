import json
import time

import pytest
import tango
from tango import DevState

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.integration.common import (
    assert_event_arrived,
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import logger


@pytest.mark.post_deployment
def test_tmc_state(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    pytest.event_arrived = False

    def event_callback(evt):
        assert not evt.err
        logger.info(evt.attr_value.value)
        if evt.attr_value.value == DevState.FAULT:
            pytest.event_arrived = True

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "TMOpState",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    ensure_checked_devices(central_node)

    csp_master_ln = dev_factory.get_device("ska_mid/tm_leaf_node/csp_master")
    sdp_master_ln = dev_factory.get_device("ska_mid/tm_leaf_node/sdp_master")
    csp_subarray_ln = dev_factory.get_device(
        "ska_mid/tm_leaf_node/csp_subarray01"
    )
    sdp_subarray_ln = dev_factory.get_device(
        "ska_mid/tm_leaf_node/sdp_subarray01"
    )
    dish_ln = dev_factory.get_device("ska_mid/tm_leaf_node/d0001")

    # set state not handled directly by central node
    csp_master_ln.SetDirectState(DevState.FAULT)
    sdp_master_ln.SetDirectState(DevState.ON)
    csp_subarray_ln.SetDirectState(DevState.ON)
    sdp_subarray_ln.SetDirectState(DevState.ON)
    dish_ln.SetDirectState(DevState.ON)

    assert_event_arrived()

    assert central_node.TMOpState == DevState.FAULT

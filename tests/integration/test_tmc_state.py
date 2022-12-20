import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from tests.integration.common import devices_to_load  # noqa F401
from tests.integration.common import ensure_checked_devices
from tests.settings import logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_tmc_state_mid(tango_context, change_event_callbacks):

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "tmOpState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["tmOpState"],
    )

    csp_master_ln = dev_factory.get_device("ska_mid/tm_leaf_node/csp_master")
    sdp_master_ln = dev_factory.get_device("ska_mid/tm_leaf_node/sdp_master")
    csp_subarray_ln = dev_factory.get_device(
        "ska_mid/tm_leaf_node/csp_subarray01"
    )
    sdp_subarray_ln = dev_factory.get_device(
        "ska_mid/tm_leaf_node/sdp_subarray01"
    )
    dish_ln = dev_factory.get_device("ska_mid/tm_leaf_node/d0001")

    csp_master_ln.SetDirectState(DevState.FAULT)
    sdp_master_ln.SetDirectState(DevState.ON)
    csp_subarray_ln.SetDirectState(DevState.ON)
    sdp_subarray_ln.SetDirectState(DevState.ON)
    dish_ln.SetDirectState(DevState.ON)
    change_event_callbacks["tmOpState"].assert_change_event(
        DevState.FAULT, lookahead=2
    )
    assert central_node.tmOpState == DevState.FAULT


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_tmc_state_low(tango_context, change_event_callbacks):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_low/tm_central/central_node")

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "tmOpState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["tmOpState"],
    )

    csp_master_ln = dev_factory.get_device("ska_low/tm_leaf_node/csp_master")
    sdp_master_ln = dev_factory.get_device("ska_low/tm_leaf_node/sdp_master")
    csp_subarray_ln = dev_factory.get_device(
        "ska_low/tm_leaf_node/csp_subarray01"
    )
    sdp_subarray_ln = dev_factory.get_device(
        "ska_low/tm_leaf_node/sdp_subarray01"
    )

    csp_master_ln.SetDirectState(DevState.FAULT)
    sdp_master_ln.SetDirectState(DevState.ON)
    csp_subarray_ln.SetDirectState(DevState.ON)
    sdp_subarray_ln.SetDirectState(DevState.ON)

    change_event_callbacks["tmOpState"].assert_change_event(
        DevState.FAULT, lookahead=2
    )
    assert central_node.tmOpState == DevState.FAULT

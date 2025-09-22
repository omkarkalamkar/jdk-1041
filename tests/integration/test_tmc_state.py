"""Tests tmc State"""

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
    DISH_LEAF_NODE_1,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SUBARRAY_LN,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SUBARRAY_LN,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SUBARRAY_LN,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SUBARRAY_LN,
)
from tests.integration.conftest import ensure_checked_devices


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_tmc_state_mid(change_event_callbacks):
    """Tests tmc state for mid"""

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "tmOpState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["tmOpState"],
    )

    csp_master_ln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_master_ln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_subarray_ln = dev_factory.get_device(MID_CSP_SUBARRAY_LN)
    sdp_subarray_ln = dev_factory.get_device(MID_SDP_SUBARRAY_LN)
    dish_ln = dev_factory.get_device(DISH_LEAF_NODE_1)

    csp_master_ln.SetDirectState(DevState.FAULT)
    sdp_master_ln.SetDirectState(DevState.ON)
    csp_subarray_ln.SetDirectState(DevState.ON)
    sdp_subarray_ln.SetDirectState(DevState.ON)
    dish_ln.SetDirectState(DevState.ON)
    change_event_callbacks["tmOpState"].assert_change_event(
        DevState.FAULT, lookahead=4
    )
    assert central_node.tmOpState == DevState.FAULT


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_tmc_state_low(change_event_callbacks):
    """Test tmc state for low"""

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "tmOpState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["tmOpState"],
    )

    csp_master_ln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    sdp_master_ln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    csp_subarray_ln = dev_factory.get_device(LOW_CSP_SUBARRAY_LN)
    sdp_subarray_ln = dev_factory.get_device(LOW_SDP_SUBARRAY_LN)

    csp_master_ln.SetDirectState(DevState.FAULT)
    sdp_master_ln.SetDirectState(DevState.ON)
    csp_subarray_ln.SetDirectState(DevState.ON)
    sdp_subarray_ln.SetDirectState(DevState.ON)

    change_event_callbacks["tmOpState"].assert_change_event(
        DevState.FAULT, lookahead=4
    )
    assert central_node.tmOpState == DevState.FAULT

"""Tests tmc State"""
import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from tests.integration.conftest import ensure_checked_devices
from tests.settings import event_remover, logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_tmc_state_mid(tango_context, change_event_callbacks):
    """Tests tmc state for mid"""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("mid-tmc/central-node/0")

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "tmOpState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["tmOpState"],
    )

    csp_master_ln = dev_factory.get_device("mid-tmc/leaf-node-csp/0")
    sdp_master_ln = dev_factory.get_device("mid-tmc/leaf-node-sdp/0")
    csp_subarray_ln = dev_factory.get_device(
        "mid-tmc/subarray-leaf-node-csp/01"
    )
    sdp_subarray_ln = dev_factory.get_device(
        "mid-tmc/subarray-leaf-node-sdp/01"
    )
    dish_ln = dev_factory.get_device("mid-tmc/leaf-node-dish/ska001")

    csp_master_ln.SetDirectState(DevState.FAULT)
    sdp_master_ln.SetDirectState(DevState.ON)
    csp_subarray_ln.SetDirectState(DevState.ON)
    sdp_subarray_ln.SetDirectState(DevState.ON)
    dish_ln.SetDirectState(DevState.ON)
    change_event_callbacks["tmOpState"].assert_change_event(
        DevState.FAULT, lookahead=4
    )
    assert central_node.tmOpState == DevState.FAULT
    event_remover(
        change_event_callbacks,
        ["tmOpState"],
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_tmc_state_low(tango_context, change_event_callbacks):
    """Test tmc state for low"""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("low-tmc/central-node/0")

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "tmOpState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["tmOpState"],
    )

    csp_master_ln = dev_factory.get_device("low-tmc/leaf-node-csp/0")
    sdp_master_ln = dev_factory.get_device("low-tmc/leaf-node-sdp/0")
    csp_subarray_ln = dev_factory.get_device(
        "low-tmc/subarray-leaf-node-csp/01"
    )
    sdp_subarray_ln = dev_factory.get_device(
        "low-tmc/subarray-leaf-node-sdp/01"
    )

    csp_master_ln.SetDirectState(DevState.FAULT)
    sdp_master_ln.SetDirectState(DevState.ON)
    csp_subarray_ln.SetDirectState(DevState.ON)
    sdp_subarray_ln.SetDirectState(DevState.ON)

    change_event_callbacks["tmOpState"].assert_change_event(
        DevState.FAULT, lookahead=4
    )
    assert central_node.tmOpState == DevState.FAULT
    event_remover(
        change_event_callbacks,
        ["tmOpState"],
    )

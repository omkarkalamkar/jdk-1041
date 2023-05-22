import json
import time
import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    logger
)


def telescope_availability(
    tango_context, central_node_fqdn, change_event_callbacks
):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_fqdn)
    if "ska_mid" in central_node_fqdn:
        csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
        sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
        subarray_node = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    else:
        csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
        sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
        subarray_node = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    # central_node.subscribe_event(
    #     "telescopeAvailability",
    #     tango.EventType.CHANGE_EVENT,
    #     change_event_callbacks["telescopeAvailability"],
    # )
    val = central_node.read_attribute("telescopeAvailability").value
    logger.info(f"val: {val}")
    subarray_node.SetisSubarrayAvailable(True)
    csp_mln.SetisSubsystemAvailable(False)
    sdp_mln.SetisSubsystemAvailable(False)
    time.sleep(1)
    val1 = central_node.read_attribute("telescopeAvailability").value
    logger.info(f"val: {val1}")
    # expected_result = json.dumps(
    #     '{"tmc_subarrays": {"ska_mid/tm_subarray_node/1": False},\
    #         "csp_master_leaf_node": False,"sdp_master_leaf_node": False,}'
    # )

    # change_event_callbacks.assert_change_event(
    #     "telescopeAvailability",
    #     expected_result,
    #     lookahead=2,
    # )

    # subarray_node.SetIsSubarrayAvailable(True)
    # csp_mln.SetisSubsystemAvailable(True)
    # sdp_mln.SetisSubsystemAvailable(True)
    # expected_result = json.dumps(
    #     '{"tmc_subarrays": {"ska_mid/tm_subarray_node/1": True},\
    #         "csp_master_leaf_node": True,"sdp_master_leaf_node": True,}'
    # )

    # change_event_callbacks.assert_change_event(
    #     "telescopeAvailability",
    #     expected_result,
    #     lookahead=2,
    # )

@pytest.mark.ava
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_availability_mid(tango_context, change_event_callbacks):
    telescope_availability(
        tango_context,
        "ska_mid/tm_central/central_node",
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_telescope_availability_low(tango_context, change_event_callbacks):
    telescope_availability(
        tango_context,
        "ska_low/tm_central/central_node",
        change_event_callbacks,
    )

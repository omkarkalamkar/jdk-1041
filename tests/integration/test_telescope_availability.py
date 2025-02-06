"""Test case file"""
import json
import time

import pytest
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_MLN_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    TIMEOUT,
    check_subarray_availability,
    logger,
)

# TODO: For future reference.
# def check_subarray_availability(central_node, subarray_fqdn,
# expected_status):
#     start_time = time.time()
#     elapsed_time = 0
#     while (json.loads(central_node.telescopeAvailability))["tmc_subarrays"][
#         subarray_fqdn
#     ] != expected_status:
#         elapsed_time = time.time() - start_time
#         time.sleep(0.1)
#         if elapsed_time > TIMEOUT:
#             pytest.fail(
#             "Timeout occurred while checking the SubarrayNode availability."
#             )


def check_cspmln_availability(central_node, expected_status):
    """checks cspmln availablity"""
    start_time = time.time()
    elapsed_time = 0
    while (json.loads(central_node.telescopeAvailability))[
        "csp_master_leaf_node"
    ] != expected_status:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking \
                    the CspMasterLeafNode availability."
            )


def check_sdpmln_availability(central_node, expected_status):
    """checks sdpmln availablity"""
    start_time = time.time()
    elapsed_time = 0
    while (json.loads(central_node.telescopeAvailability))[
        "sdp_master_leaf_node"
    ] != expected_status:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking \
                the SdpMasterLeafNode availability."
            )


def check_mccsmln_availability(central_node, expected_status):
    """Checks mccsmln availability"""
    start_time = time.time()
    elapsed_time = 0
    while (json.loads(central_node.telescopeAvailability))[
        "mccs_master_leaf_node"
    ] != expected_status:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the\
              MccsMasterLeafNode availability."
            )


def telescope_availability(
    tango_context, central_node_fqdn, change_event_callbacks
):
    """Checks telescope availability"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_fqdn)
    if "ska_mid" in central_node_fqdn:
        csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
        sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
        subarray_node = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    else:
        mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
        csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
        sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
        subarray_node = dev_factory.get_device(LOW_SUBARRAY_DEVICE)

    subarray_node.SetisSubarrayAvailable(False)
    assert subarray_node.isSubarrayAvailable is False

    csp_mln.SetSubsystemAvailable(False)
    assert csp_mln.isSubsystemAvailable is False

    sdp_mln.SetSubsystemAvailable(False)
    assert sdp_mln.isSubsystemAvailable is False

    if "ska_mid" in central_node_fqdn:
        check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, False)
    else:
        check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, False)
        mccs_mln.SetSubsystemAvailable(False)
        assert mccs_mln.isSubsystemAvailable is False
        check_mccsmln_availability(central_node, False)

    check_cspmln_availability(central_node, False)
    check_sdpmln_availability(central_node, False)

    logger.info(
        "telescopeAvailability attribute value:%s",
        central_node.telescopeAvailability,
    )

    subarray_node.SetisSubarrayAvailable(True)
    assert subarray_node.isSubarrayAvailable is True

    csp_mln.SetSubsystemAvailable(True)
    assert csp_mln.isSubsystemAvailable is True

    sdp_mln.SetSubsystemAvailable(True)
    assert sdp_mln.isSubsystemAvailable is True

    if "ska_mid" in central_node_fqdn:
        check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)
    else:
        check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)
        mccs_mln.SetSubsystemAvailable(True)
        assert mccs_mln.isSubsystemAvailable is True
        check_mccsmln_availability(central_node, True)

    logger.info(
        "telescopeAvailability attribute value:%s",
        central_node.telescopeAvailability,
    )

    check_cspmln_availability(central_node, True)
    check_sdpmln_availability(central_node, True)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_availability_mid(tango_context, change_event_callbacks):
    """Tests telescope availability mid"""
    telescope_availability(
        tango_context,
        "mid-tmc/central-node/0",
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_telescope_availability_low(tango_context, change_event_callbacks):
    """Tests telescope availability mid"""
    telescope_availability(
        tango_context,
        "low-tmc/central-node/0",
        change_event_callbacks,
    )

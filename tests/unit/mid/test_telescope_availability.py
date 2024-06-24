"""Test cases file"""
import time

import pytest
from ska_tmc_common import (
    HelperBaseDevice,
    HelperDishDevice,
    HelperDishLNDevice,
)
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.model.input import InputParameterMid
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    TIMEOUT,
    check_cspmln_availability,
    check_sdpmln_availability,
    create_cm_no_faulty_devices,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
            ],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_SDP_MLN_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
            ],
        },
        {
            "class": HelperDishLNDevice,
            "devices": [
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
        {
            "class": HelperDishDevice,
            "devices": [
                {"name": DISH_MASTER_DEVICE},
            ],
        },
    )


def test_check_telescope_availability_attribute_initial_events(tango_context):
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterMid(None)
    )
    check_subarray_availability(cm, MID_SUBARRAY_DEVICE, False)
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_mln.SetSubsystemAvailable(False)
    sdp_mln.SetSubsystemAvailable(False)
    check_cspmln_availability(cm, False)
    check_sdpmln_availability(cm, False)
    assert (cm.component.telescope_availability)["tmc_subarrays"][
        MID_SUBARRAY_DEVICE
    ] is False
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is False
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is False


def test_telescope_availability_with_subarray_and_master_leaf_nodes(
    tango_context,
):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    dev_factory = DevFactory()
    subarray_node = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    subarray_node.SetisSubarrayAvailable(True)
    csp_mln.SetSubsystemAvailable(True)
    sdp_mln.SetSubsystemAvailable(True)

    check_subarray_availability(cm, MID_SUBARRAY_DEVICE, True)
    check_cspmln_availability(cm, True)
    check_sdpmln_availability(cm, True)
    assert (cm.component.telescope_availability)["tmc_subarrays"][
        MID_SUBARRAY_DEVICE
    ] is True
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is True
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is True


def check_subarray_availability(cm, subarray_fqdn, expected_status):
    start_time = time.time()
    elapsed_time = 0
    while (cm.component.telescope_availability)["tmc_subarrays"][
        subarray_fqdn
    ] != expected_status:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the SubarrayNode"
                + " availability."
            )

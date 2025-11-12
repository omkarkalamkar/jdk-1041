"""Test cases file"""

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_simulators import HelperBaseDevice
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice

from ska_tmc_centralnode.model.enum import ModesAvailability
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
    create_cm_no_faulty_devices,
    ensure_imaging,
    set_devices_state,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invokation"""
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
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
                {"name": DISH_MASTER_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def test_imaging_available(tango_context):
    """Test imaging available."""
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_state(
        devices=[
            MID_CSP_MASTER_DEVICE,
            DISH_MASTER_DEVICE,
        ],
        devFactory=DevFactory(),
        state=tango.DevState.ON,
    )
    ensure_imaging(cm, ModesAvailability.available, expected_elapsed_time=30)
    # Here expected elapsed time is set to 12 since  set_state() API is taking
    # more time to set the state and hence actual elapsed time is increasing
    assert cm.component.imaging == ModesAvailability.available

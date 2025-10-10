"""Test cases file"""

import pytest
import tango
from ska_tmc_common import (
    HelperBaseDevice,
    HelperDishDevice,
    HelperDishLNDevice,
)
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice

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
    ensure_tmc_op_state,
    set_devices_state,
)


@pytest.fixture()
def devices_to_load():
    """Devices which needs to be loaded"""
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


def set_devices_on(cm, devFactory, expected_elapsed_time):
    """sets the given devices to ON"""
    set_devices_state(
        devices=[
            MID_SUBARRAY_DEVICE,
            MID_CSP_SLN_DEVICE,
            MID_SDP_SLN_DEVICE,
            MID_CSP_MLN_DEVICE,
            MID_SDP_MLN_DEVICE,
            DISH_LEAF_NODE_DEVICE,
        ],
        devFactory=devFactory,
        state=tango.DevState.ON,
    )
    ensure_tmc_op_state(cm, tango.DevState.ON, expected_elapsed_time)


@pytest.mark.skip(reason="behaviour for this test case is not stable")
def test_tmc_state_on(tango_context):
    """Tests tmc stats is on"""
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_on(
        cm, devFactory, 30
    )  # Here expected elapsed time is set to 20 since  set_state()
    # API is taking more time to set the state and hence actual elapsed
    # time is increasing
    assert cm.component.tmc_op_state == tango.DevState.ON

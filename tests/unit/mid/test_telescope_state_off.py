"""Test cases file"""

import pytest
import tango
from ska_tmc_simulators import (
    HelperBaseDevice,
    HelperDishDevice,
    HelperDishLNDevice,
)
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode
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
    ensure_telescope_state,
    set_devices_state,
)


@pytest.fixture()
def devices_to_load():
    """devices to load for command invokation"""
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


def test_telescope_state_off_with_dishmode_standbylp(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_state(
        devices=[
            MID_CSP_MASTER_DEVICE,
            MID_SDP_MASTER_DEVICE,
        ],
        state=tango.DevState.OFF,
        devFactory=DevFactory(),
    )

    dish_master = DevFactory().get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    # Here expected elapsed time is set to 12 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=30)
    assert cm.component.telescope_state == tango.DevState.OFF


def test_telescope_state_off_with_dishmode_shutdown(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_state(
        devices=[
            MID_CSP_MASTER_DEVICE,
            MID_SDP_MASTER_DEVICE,
        ],
        state=tango.DevState.OFF,
        devFactory=DevFactory(),
    )

    dish_master = DevFactory().get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.SHUTDOWN)
    # Here expected elapsed time is set to 12 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=30)
    assert cm.component.telescope_state == tango.DevState.OFF

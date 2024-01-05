import pytest
import tango
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode
from ska_tmc_common.test_helpers.helper_dish_device import HelperDishDevice
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)

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
    set_device_state,
    set_dish_mode,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
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


def set_device_init(devFactory, cm, expected_elapsed_time):
    set_device_state(MID_CSP_MASTER_DEVICE, tango.DevState.INIT, devFactory)
    set_device_state(MID_SDP_MASTER_DEVICE, tango.DevState.DISABLE, devFactory)
    set_device_state(DISH_MASTER_DEVICE, tango.DevState.OFF, devFactory)
    ensure_telescope_state(cm, tango.DevState.INIT, expected_elapsed_time)


def test_telescope_state_init(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_init(
        devFactory, cm, 15
    )  # Here expected elapsed time is set to 12 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    assert cm.component.telescope_state == tango.DevState.INIT


def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    set_device_state(MID_CSP_MASTER_DEVICE, tango.DevState.FAULT, devFactory)
    set_device_state(MID_SDP_MASTER_DEVICE, tango.DevState.STANDBY, devFactory)
    set_device_state(DISH_MASTER_DEVICE, tango.DevState.OFF, devFactory)
    ensure_telescope_state(cm, tango.DevState.FAULT, expected_elapsed_time)


def test_telescope_state_fault_over_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_one_device_fault(devFactory, cm, 15)
    assert cm.component.telescope_state == tango.DevState.FAULT


def set_device_standby(devFactory, cm, expected_elapsed_time):
    set_device_state(MID_CSP_MASTER_DEVICE, tango.DevState.STANDBY, devFactory)
    set_device_state(MID_SDP_MASTER_DEVICE, tango.DevState.ON, devFactory)
    set_dish_mode(DISH_MASTER_DEVICE, DishMode.STANDBY_LP, devFactory)
    ensure_telescope_state(cm, tango.DevState.STANDBY, expected_elapsed_time)


def test_telescope_state_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_standby(
        devFactory, cm, 15
    )  # Here expected elapsed time is set to 15 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    assert cm.component.telescope_state == tango.DevState.STANDBY

"""Test cases file"""

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode
from ska_tmc_simulators import (
    HelperBaseDevice,
    HelperDishDevice,
    HelperDishLNDevice,
)
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice

from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_LEAF_NODE_DEVICE_099,
    DISH_LEAF_NODE_DEVICE_500,
    DISH_LEAF_NODE_DEVICE_999,
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
            ],
        },
        {
            "class": HelperDishLNDevice,
            "devices": [
                {"name": DISH_LEAF_NODE_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE_099},
                {"name": DISH_LEAF_NODE_DEVICE_500},
                {"name": DISH_LEAF_NODE_DEVICE_999},
            ],
        },
        {
            "class": HelperDishDevice,
            "devices": [
                {"name": DISH_MASTER_DEVICE},
            ],
        },
    )


def set_device_init(dev_factory, cm, expected_elapsed_time):
    """initialises devices"""
    set_device_state(MID_CSP_MASTER_DEVICE, tango.DevState.INIT, dev_factory)
    set_device_state(
        MID_SDP_MASTER_DEVICE, tango.DevState.DISABLE, dev_factory
    )
    set_device_state(DISH_MASTER_DEVICE, tango.DevState.OFF, dev_factory)
    ensure_telescope_state(cm, tango.DevState.INIT, expected_elapsed_time)


def test_telescope_state_init(tango_context):
    """Test telescope state initialisation."""
    dev_factory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_init(
        dev_factory, cm, 30
    )  # Here expected elapsed time is set to 12 since  set_state()
    # API is taking more time to set the state and hence actual elapsed
    # time is increasing
    assert cm.component.telescope_state == tango.DevState.INIT


def set_one_device_fault(dev_factory, cm, expected_elapsed_time):
    """Sets one device faulty"""
    set_device_state(MID_CSP_MASTER_DEVICE, tango.DevState.FAULT, dev_factory)
    set_device_state(
        MID_SDP_MASTER_DEVICE, tango.DevState.STANDBY, dev_factory
    )
    set_device_state(DISH_MASTER_DEVICE, tango.DevState.OFF, dev_factory)
    ensure_telescope_state(cm, tango.DevState.FAULT, expected_elapsed_time)


def test_telescope_state_fault_over_standby(tango_context):
    """Test telescope state fault over standby"""
    dev_factory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_one_device_fault(dev_factory, cm, 40)
    assert cm.component.telescope_state == tango.DevState.FAULT


def set_device_standby(dev_factory, cm, expected_elapsed_time):
    """Sets device to standby"""
    set_device_state(
        MID_CSP_MASTER_DEVICE, tango.DevState.STANDBY, dev_factory
    )
    set_device_state(MID_SDP_MASTER_DEVICE, tango.DevState.ON, dev_factory)
    for dish in [
        DISH_LEAF_NODE_DEVICE,
        DISH_LEAF_NODE_DEVICE_099,
        DISH_LEAF_NODE_DEVICE_500,
        DISH_LEAF_NODE_DEVICE_999,
    ]:
        set_dish_mode(dish, DishMode.STANDBY_LP, dev_factory)

    ensure_telescope_state(cm, tango.DevState.STANDBY, expected_elapsed_time)


def test_telescope_state_standby(tango_context):
    """Tests telescope state standby"""
    dev_factory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_standby(
        dev_factory, cm, 40
    )  # Here expected elapsed time is set to 15 since  set_state()
    # API is taking more time to set the state and hence actual elapsed
    # time is increasing
    assert cm.component.telescope_state == tango.DevState.STANDBY

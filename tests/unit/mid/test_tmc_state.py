import pytest
import tango
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.dev_factory import DevFactory
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
    ensure_tmc_op_state,
    set_device_state,
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
                {"name": DISH_MASTER_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def set_device_init(devFactory, cm, expected_elapsed_time):
    """initialise device"""
    set_device_state(
        "ska_mid/tm_subarray_node/1", tango.DevState.INIT, devFactory
    )
    ensure_tmc_op_state(cm, tango.DevState.INIT, expected_elapsed_time)


def test_tmc_state_init(tango_context):
    """tests tmc state initialisation"""
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_init(devFactory, cm, 15)
    assert cm.component.tmc_op_state == tango.DevState.INIT


def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "ska_mid/tm_subarray_node/1", tango.DevState.FAULT, devFactory
    )
    set_device_state(
        "ska_mid/tm_leaf_node/csp_subarray01", tango.DevState.OFF, devFactory
    )
    set_device_state(
        "ska_mid/tm_leaf_node/sdp_subarray01", tango.DevState.OFF, devFactory
    )
    set_device_state(
        "ska_mid/tm_leaf_node/csp_master", tango.DevState.STANDBY, devFactory
    )
    set_device_state(
        "ska_mid/tm_leaf_node/sdp_master", tango.DevState.STANDBY, devFactory
    )
    ensure_tmc_op_state(cm, tango.DevState.FAULT, expected_elapsed_time)


def test_tmc_state_fault_over_standby(tango_context):
    """tests for tmc state fault over standby"""
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_one_device_fault(devFactory, cm, 15)
    assert cm.component.tmc_op_state == tango.DevState.FAULT


def set_device_standby(devFactory, cm, expected_elapsed_time):
    """sets device to standby"""
    set_device_state(
        "ska_mid/tm_subarray_node/1", tango.DevState.STANDBY, devFactory
    )
    set_device_state(
        "ska_mid/tm_leaf_node/csp_subarray01", tango.DevState.OFF, devFactory
    )
    set_device_state(
        "ska_mid/tm_leaf_node/sdp_subarray01", tango.DevState.OFF, devFactory
    )
    set_device_state(
        "ska_mid/tm_leaf_node/csp_master", tango.DevState.ON, devFactory
    )
    set_device_state(
        "ska_mid/tm_leaf_node/sdp_master", tango.DevState.ON, devFactory
    )
    ensure_tmc_op_state(cm, tango.DevState.STANDBY, expected_elapsed_time)

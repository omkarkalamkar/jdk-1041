import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    LOW_CSP_CONTROL_DEVICE,
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_SUBARRAY_DEVICE,
    LOW_SDP_CONTROL_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_SUBARRAY_DEVICE,
    LOW_SUBARRAY_DEVICE,
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
                {"name": LOW_SUBARRAY_DEVICE},
                {"name": LOW_SDP_SUBARRAY_DEVICE},
                {"name": LOW_CSP_SUBARRAY_DEVICE},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": LOW_CSP_MASTER_DEVICE},
                {"name": LOW_CSP_CONTROL_DEVICE},
                {"name": LOW_SDP_MASTER_DEVICE},
                {"name": LOW_SDP_CONTROL_DEVICE},
            ],
        },
    )


def set_device_init(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "ska_low/tm_subarray_node/1", tango.DevState.INIT, devFactory
    )
    ensure_tmc_op_state(cm, tango.DevState.INIT, expected_elapsed_time)


@pytest.mark.SKA_low
def test_tmc_state_init(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_init(devFactory, cm, 15)
    assert cm.component.tmc_op_state == tango.DevState.INIT


def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "ska_low/tm_subarray_node/1", tango.DevState.FAULT, devFactory
    )
    set_device_state(
        "ska_low/tm_leaf_node/csp_master", tango.DevState.OFF, devFactory
    )
    set_device_state(
        "ska_low/tm_leaf_node/sdp_master", tango.DevState.STANDBY, devFactory
    )
    ensure_tmc_op_state(cm, tango.DevState.FAULT, expected_elapsed_time)


@pytest.mark.SKA_low
def test_tmc_state_fault_over_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_one_device_fault(devFactory, cm, 15)
    assert cm.component.tmc_op_state == tango.DevState.FAULT


def set_device_standby(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "ska_low/tm_subarray_node/1", tango.DevState.STANDBY, devFactory
    )
    set_device_state(
        "ska_low/tm_leaf_node/csp_master", tango.DevState.OFF, devFactory
    )
    set_device_state(
        "ska_low/tm_leaf_node/sdp_master", tango.DevState.ON, devFactory
    )
    ensure_tmc_op_state(cm, tango.DevState.STANDBY, expected_elapsed_time)

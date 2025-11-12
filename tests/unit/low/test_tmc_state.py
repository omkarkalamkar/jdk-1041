"""Test case module"""

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_simulators import (
    HelperBaseDevice,
    HelperMCCSController,
    HelperMCCSMasterLeafNode,
)
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SLN_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_CONTROLLER,
    MCCS_MLN_DEVICE,
    create_cm_no_faulty_devices,
    ensure_tmc_op_state,
    set_device_state,
)


@pytest.fixture()
def devices_to_load():
    """List of devices to load for command invocation"""
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
                {"name": LOW_SDP_SLN_DEVICE},
                {"name": LOW_CSP_SLN_DEVICE},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
                {"name": LOW_CSP_MASTER_DEVICE},
                {"name": LOW_SDP_MLN_DEVICE},
                {"name": LOW_SDP_MASTER_DEVICE},
            ],
        },
        {
            "class": HelperMCCSMasterLeafNode,
            "devices": [
                {"name": MCCS_MLN_DEVICE},
            ],
        },
        {
            "class": HelperMCCSController,
            "devices": [
                {"name": MCCS_CONTROLLER},
            ],
        },
    )


def set_device_init(devFactory, cm, expected_elapsed_time):
    """Sets the devices init"""
    set_device_state(LOW_SUBARRAY_DEVICE, tango.DevState.INIT, devFactory)
    ensure_tmc_op_state(cm, tango.DevState.INIT, expected_elapsed_time)


@pytest.mark.SKA_low
def test_tmc_state_init(tango_context):
    """Test tmc state init"""
    # import debugpy; debugpy.debug_this_thread()
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_init(devFactory, cm, 30)
    assert cm.component.tmc_op_state == tango.DevState.INIT


def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    """Sets one devices fault"""
    set_device_state(LOW_SUBARRAY_DEVICE, tango.DevState.FAULT, devFactory)
    set_device_state(LOW_CSP_MLN_DEVICE, tango.DevState.OFF, devFactory)
    set_device_state(LOW_SDP_MLN_DEVICE, tango.DevState.STANDBY, devFactory)
    ensure_tmc_op_state(cm, tango.DevState.FAULT, expected_elapsed_time)


@pytest.mark.SKA_low
def test_tmc_state_fault_over_standby(tango_context):
    """Test tmc state fault over standby"""
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_one_device_fault(devFactory, cm, 30)
    assert cm.component.tmc_op_state == tango.DevState.FAULT


def set_device_standby(devFactory, cm, expected_elapsed_time):
    """sets devices standby"""
    set_device_state(LOW_SUBARRAY_DEVICE, tango.DevState.STANDBY, devFactory)
    set_device_state(LOW_CSP_MLN_DEVICE, tango.DevState.OFF, devFactory)
    set_device_state(LOW_SDP_MLN_DEVICE, tango.DevState.ON, devFactory)
    ensure_tmc_op_state(cm, tango.DevState.STANDBY, expected_elapsed_time)

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
    ensure_telescope_state,
    set_device_state,
)


@pytest.fixture()
def devices_to_load():
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


def set_device_init(dev_factory, cm, expected_elapsed_time):
    set_device_state(LOW_SDP_MASTER_DEVICE, tango.DevState.INIT, dev_factory)
    set_device_state(LOW_CSP_MASTER_DEVICE, tango.DevState.INIT, dev_factory)
    ensure_telescope_state(cm, tango.DevState.INIT, expected_elapsed_time)


@pytest.mark.SKA_low
def test_telescope_state_init(tango_context):
    dev_factory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_init(dev_factory, cm, 30)
    assert cm.component.telescope_state == tango.DevState.INIT


def set_one_device_fault(dev_factory, cm, expected_elapsed_time):
    set_device_state(LOW_SDP_MASTER_DEVICE, tango.DevState.FAULT, dev_factory)
    ensure_telescope_state(cm, tango.DevState.FAULT, expected_elapsed_time)


@pytest.mark.skip(reason="TODO")
@pytest.mark.SKA_low
def test_telescope_state_fault_over_standby(tango_context):
    dev_factory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_one_device_fault(dev_factory, cm, 40)
    assert cm.component.telescope_state == tango.DevState.FAULT


def set_device_standby(dev_factory, cm, expected_elapsed_time):
    set_device_state(
        LOW_SDP_MASTER_DEVICE, tango.DevState.STANDBY, dev_factory
    )
    set_device_state(
        LOW_CSP_MASTER_DEVICE, tango.DevState.STANDBY, dev_factory
    )
    ensure_telescope_state(cm, tango.DevState.STANDBY, expected_elapsed_time)


@pytest.mark.SKA_low
def test_telescope_state_standby(tango_context):
    dev_factory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_standby(dev_factory, cm, 40)
    assert cm.component.telescope_state == tango.DevState.STANDBY

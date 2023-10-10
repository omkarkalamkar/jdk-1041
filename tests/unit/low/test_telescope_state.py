import pytest
import tango
from ska_tmc_common import (
    HelperBaseDevice,
    HelperMCCSController,
    HelperMCCSMasterLeafNode,
)
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)

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
            "class": HelperSubArrayDevice,
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
    set_device_state("low-sdp/control/0", tango.DevState.INIT, devFactory)
    set_device_state("low-csp/control/0", tango.DevState.INIT, devFactory)
    ensure_telescope_state(cm, tango.DevState.INIT, expected_elapsed_time)


@pytest.mark.SKA_low
def test_telescope_state_init(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_init(devFactory, cm, 15)
    assert cm.component.telescope_state == tango.DevState.INIT


def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    set_device_state("low-sdp/control/0", tango.DevState.FAULT, devFactory)
    ensure_telescope_state(cm, tango.DevState.FAULT, expected_elapsed_time)


@pytest.mark.SKA_low
def test_telescope_state_fault_over_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_one_device_fault(devFactory, cm, 15)
    assert cm.component.telescope_state == tango.DevState.FAULT


def set_device_standby(devFactory, cm, expected_elapsed_time):
    set_device_state("low-sdp/control/0", tango.DevState.STANDBY, devFactory)
    set_device_state("low-csp/control/0", tango.DevState.STANDBY, devFactory)
    ensure_telescope_state(cm, tango.DevState.STANDBY, expected_elapsed_time)


@pytest.mark.SKA_low
def test_telescope_state_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_standby(devFactory, cm, 15)
    assert cm.component.telescope_state == tango.DevState.STANDBY

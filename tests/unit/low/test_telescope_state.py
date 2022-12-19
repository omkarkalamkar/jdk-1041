import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    create_cm_no_faulty_devices,
    ensure_telescope_state,
    set_device_state,
)


def set_device_init(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "low-mccs/control/control", tango.DevState.INIT, devFactory
    )
    ensure_telescope_state(cm, tango.DevState.INIT, expected_elapsed_time)


@pytest.mark.skip("Needs update in helper devices")
@pytest.mark.SKA_low
def test_telescope_state_init(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_init(devFactory, cm, 15)
    assert cm.component.telescope_state == tango.DevState.INIT


def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "low-mccs/control/control", tango.DevState.FAULT, devFactory
    )
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
    set_device_state(
        "low-mccs/control/control", tango.DevState.STANDBY, devFactory
    )
    ensure_telescope_state(cm, tango.DevState.STANDBY, expected_elapsed_time)


@pytest.mark.SKA_low
def test_telescope_state_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_standby(devFactory, cm, 15)
    assert cm.component.telescope_state == tango.DevState.STANDBY

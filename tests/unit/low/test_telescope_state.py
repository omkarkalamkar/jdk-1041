import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
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
                {"name": "ska_low/tm_subarray_node/1"},
                {"name": "ska_low/tm_leaf_node/mccs_subarray01"},
            ],
        },
        {
            "class": HelperMCCSStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
                {"name": "low-mccs/control/control"},
            ],
        },
    )


def set_device_init(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "low-mccs/control/control", tango.DevState.INIT, devFactory
    )
    ensure_telescope_state(cm, tango.DevState.INIT, expected_elapsed_time)


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_init(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_init(devFactory, cm, 1.5)
    assert cm.component.telescope_state == tango.DevState.INIT


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_init_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, False, InputParameterLow(None)
    )
    set_device_init(devFactory, cm, 1.5)
    assert cm.component.telescope_state == tango.DevState.INIT


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_init_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, False, True, InputParameterLow(None)
    )
    set_device_init(devFactory, cm, 2)
    assert cm.component.telescope_state == tango.DevState.INIT


def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "low-mccs/control/control", tango.DevState.FAULT, devFactory
    )
    ensure_telescope_state(cm, tango.DevState.FAULT, expected_elapsed_time)


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_fault_over_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_one_device_fault(devFactory, cm, 5)
    assert cm.component.telescope_state == tango.DevState.FAULT


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_fault_over_standby_only_monitoring_loop(
    tango_context,
):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, False, InputParameterLow(None)
    )
    set_one_device_fault(devFactory, cm, 1.5)
    assert cm.component.telescope_state == tango.DevState.FAULT


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_fault_over_standby_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, False, True, InputParameterLow(None)
    )
    set_one_device_fault(devFactory, cm, 2)
    assert cm.component.telescope_state == tango.DevState.FAULT


def set_device_standby(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "low-mccs/control/control", tango.DevState.STANDBY, devFactory
    )
    ensure_telescope_state(cm, tango.DevState.STANDBY, expected_elapsed_time)


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_standby(devFactory, cm, 1.5)
    assert cm.component.telescope_state == tango.DevState.STANDBY


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_standby_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, False, InputParameterLow(None)
    )
    set_device_standby(devFactory, cm, 1.5)
    assert cm.component.telescope_state == tango.DevState.STANDBY


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
def test_telescope_state_standby_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, False, True, InputParameterLow(None)
    )
    set_device_standby(devFactory, cm, 2)
    assert cm.component.telescope_state == tango.DevState.STANDBY

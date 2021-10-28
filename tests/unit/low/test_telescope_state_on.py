import pytest
import tango

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from ska_tmc_centralnode_mid.model.input import InputParameterLow
from tests.helper_state_mccsdevice import HelperMCCSStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    create_cm_no_faulty_devices,
    ensure_telescope_state,
    set_devices_state,
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


def set_devices_on(cm, devFactory, expected_elapsed_time):
    set_devices_state(
        devices=[
            "low-mccs/control/control",
        ],
        devFactory=devFactory,
        state=tango.DevState.ON,
        cm=cm,
        expected_elapsed_time=expected_elapsed_time,
    )
    ensure_telescope_state(cm, tango.DevState.ON, expected_elapsed_time=1.5)


def test_telescope_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.telescope_state == tango.DevState.ON


def test_telescope_state_on_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, False, InputParameterLow(None)
    )
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.telescope_state == tango.DevState.ON


def test_telescope_state_on_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, False, True, InputParameterLow(None)
    )
    set_devices_on(cm, devFactory, 5)
    assert cm.component.telescope_state == tango.DevState.ON

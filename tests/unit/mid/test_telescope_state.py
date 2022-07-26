import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

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
                {"name": "ska_mid/tm_subarray_node/1"},
                {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
                {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "mid_csp/elt/master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "mid_sdp/elt/master"},
                {"name": "mid_d0001/elt/master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def set_device_init(devFactory, cm, expected_elapsed_time):
    set_device_state("mid_csp/elt/master", tango.DevState.INIT, devFactory)
    set_device_state("mid_sdp/elt/master", tango.DevState.DISABLE, devFactory)
    set_device_state("mid_d0001/elt/master", tango.DevState.OFF, devFactory)
    ensure_telescope_state(cm, tango.DevState.INIT, expected_elapsed_time)


def test_telescope_state_init(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_init(
        devFactory, cm, 15
    )  # Here expected elapsed time is set to 12 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    assert cm.component.telescope_state == tango.DevState.INIT


def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    set_device_state("mid_csp/elt/master", tango.DevState.FAULT, devFactory)
    set_device_state("mid_sdp/elt/master", tango.DevState.STANDBY, devFactory)
    set_device_state("mid_d0001/elt/master", tango.DevState.OFF, devFactory)
    ensure_telescope_state(cm, tango.DevState.FAULT, expected_elapsed_time)


def test_telescope_state_fault_over_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_one_device_fault(devFactory, cm, 15)
    assert cm.component.telescope_state == tango.DevState.FAULT


def set_device_standby(devFactory, cm, expected_elapsed_time):
    set_device_state("mid_csp/elt/master", tango.DevState.STANDBY, devFactory)
    set_device_state("mid_sdp/elt/master", tango.DevState.ON, devFactory)
    set_device_state("mid_d0001/elt/master", tango.DevState.OFF, devFactory)
    ensure_telescope_state(cm, tango.DevState.STANDBY, expected_elapsed_time)


def test_telescope_state_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_standby(
        devFactory, cm, 15
    )  # Here expected elapsed time is set to 12 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    assert cm.component.telescope_state == tango.DevState.STANDBY

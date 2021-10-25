import pytest
import tango

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
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
                {"name": "ska_mid/tm_subarray_node/1"},
                {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
                {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": "mid_csp/elt/master"},
                {"name": "mid_sdp/elt/master"},
                {"name": "mid_d0001/elt/master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
            ],
        },
    )


def set_device_init(devFactory, cm, expected_elapsed_time):
    set_device_state(
        "ska_mid/tm_subarray_node/1", tango.DevState.INIT, devFactory
    )
    ensure_tmc_op_state(cm, tango.DevState.INIT, expected_elapsed_time)


def test_tmc_state_init(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_init(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.INIT


def test_tmc_state_init_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_device_init(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.INIT


def test_tmc_state_init_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_device_init(devFactory, cm, 2)
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
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_one_device_fault(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.FAULT


def test_tmc_state_fault_over_standby_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_one_device_fault(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.FAULT


def test_tmc_state_fault_over_standby_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_one_device_fault(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.FAULT


def set_device_standby(devFactory, cm, expected_elapsed_time):
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

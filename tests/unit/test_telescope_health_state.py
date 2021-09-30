

from ska_tango_base.subarray import SKASubarray
import time
import pytest
from ska_tango_base.control_model import HealthState
from tests.settings import count_faulty_devices, logger, TIMEOUT
from test_cm_all_working import create_cm
from test_telescope_startup import create_cm_no_faulty_devices
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from ska_tmc_centralnode_mid.dev_factory import DevFactory

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray01"
                },
                {
                    "name": "ska_mid/tm_subarray_node/1"
                },
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_leaf_node/csp_master"
                },
                {
                    "name": "mid_csp/elt/master"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_master"
                },
                {
                    "name": "mid_sdp/elt/master"
                },
                {
                    "name": "mid_d0001/elt/master"
                }
            ]
        }        
    )


def test_set_health_state_ok(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    assert cm.component.telescope_health_state == HealthState.OK

def test_set_health_state_ok_only_monitoring_loop(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    assert cm.component.telescope_health_state == HealthState.OK

def test_set_health_state_ok_only_events(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    start_time = time.time()
    elapsed_time = 0
    # need to wait for the first event to come just after the subscription
    while cm.component.telescope_health_state != HealthState.OK:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert cm.component.telescope_health_state == HealthState.OK

def set_device_degraded(devFactory, cm, expected_elapsed_time):
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.SetDirectHealthState(HealthState.DEGRADED)
    assert proxy.HealthState == HealthState.DEGRADED
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_health_state != HealthState.DEGRADED:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time

def test_set_health_state_degraded(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_degraded(devFactory, cm, 1.5)
    assert cm.component.telescope_health_state == HealthState.DEGRADED

def test_set_health_state_degraded_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_device_degraded(devFactory, cm, 1.5)
    assert cm.component.telescope_health_state == HealthState.DEGRADED

def test_set_health_state_degraded_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_device_degraded(devFactory, cm, 1.5)
    assert cm.component.telescope_health_state == HealthState.DEGRADED

def set_failed(devFactory, cm, expected_elapsed_time=1.5):
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.SetDirectHealthState(HealthState.DEGRADED)
    assert proxy.HealthState == HealthState.DEGRADED
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/1")
    proxy.SetDirectHealthState(HealthState.FAILED)
    assert proxy.HealthState == HealthState.FAILED
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_health_state != HealthState.FAILED:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time

def test_set_health_state_failed(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_failed(devFactory, cm)
    assert cm.component.telescope_health_state == HealthState.FAILED

def test_set_health_state_failed_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_failed(devFactory, cm)
    assert cm.component.telescope_health_state == HealthState.FAILED

def test_set_health_state_failed_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_failed(devFactory, cm)
    assert cm.component.telescope_health_state == HealthState.FAILED

def set_device_unknown(devFactory, cm, expected_elapsed_time=1.5):
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.SetDirectHealthState(HealthState.UNKNOWN)
    assert proxy.HealthState == HealthState.UNKNOWN
    # set_unknown(devFactory, "ska_mid/tm_subarray_node/1")
    # set_unknown(devFactory, "mid_csp/elt/master")
    # set_unknown(devFactory, "mid_sdp/elt/master")
    # set_unknown(devFactory, "ska_mid/tm_subarray_node/2")
    # set_unknown(devFactory, "ska_mid/tm_subarray_node/3")
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_health_state != HealthState.UNKNOWN:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time

def test_set_health_state_unknown(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_unknown(devFactory, cm)
    assert cm.component.telescope_health_state == HealthState.UNKNOWN

def test_set_health_state_unknown_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_device_unknown(devFactory, cm)
    assert cm.component.telescope_health_state == HealthState.UNKNOWN

def test_set_health_state_unknown_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_device_unknown(devFactory, cm)
    assert cm.component.telescope_health_state == HealthState.UNKNOWN
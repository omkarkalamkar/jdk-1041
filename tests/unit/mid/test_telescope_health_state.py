"""Test cases file"""
import time

import pytest
from ska_tango_base.control_model import HealthState
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.dev_factory import DevFactory

from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    TIMEOUT,
    create_cm_no_faulty_devices,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invokation"""
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
                {"name": MID_SUBARRAY_DEVICE},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_SDP_MLN_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
                {"name": DISH_MASTER_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def test_set_health_state_ok(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
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
    proxy = devFactory.get_device("mid-csp/control/0")
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
    set_device_degraded(
        devFactory,
        cm,
        12,  # Here expected elapsed time is set to 12 since  set_state()
        # API is taking more time to set the state and hence actual
        # elapsed time is increasing
    )
    assert cm.component.telescope_health_state == HealthState.DEGRADED


def set_failed(devFactory, cm, expected_elapsed_time=1.5):
    proxy = devFactory.get_device("mid-csp/control/0")
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
    set_failed(devFactory, cm, 15)
    assert cm.component.telescope_health_state == HealthState.FAILED


def set_device_unknown(devFactory, cm, expected_elapsed_time=12):
    proxy = devFactory.get_device("mid-csp/control/0")
    proxy.SetDirectHealthState(HealthState.UNKNOWN)
    assert proxy.HealthState == HealthState.UNKNOWN
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

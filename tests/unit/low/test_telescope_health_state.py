import time

import pytest
from ska_tango_base.control_model import HealthState
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import TIMEOUT, create_cm_no_faulty_devices


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


def test_set_health_state_ok(tango_context):
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
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
    proxy = devFactory.get_device("low-mccs/control/control")
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
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_degraded(devFactory, cm, 12)
    assert cm.component.telescope_health_state == HealthState.DEGRADED


def set_failed(devFactory, cm, expected_elapsed_time=1.5):
    proxy = devFactory.get_device("low-mccs/control/control")
    proxy.SetDirectHealthState(HealthState.DEGRADED)
    assert proxy.HealthState == HealthState.DEGRADED
    proxy = devFactory.get_device("ska_low/tm_subarray_node/1")
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
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_failed(devFactory, cm, 12)
    assert cm.component.telescope_health_state == HealthState.FAILED


def set_device_unknown(devFactory, cm, expected_elapsed_time=12):
    proxy = devFactory.get_device("low-mccs/control/control")
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
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_unknown(devFactory, cm)
    assert cm.component.telescope_health_state == HealthState.UNKNOWN

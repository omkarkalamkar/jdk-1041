"""Test case module"""

import time

import pytest
from ska_tango_base.control_model import AdminMode, HealthState
from ska_tmc_common import (
    HelperBaseDevice,
    HelperMCCSController,
    HelperMCCSMasterLeafNode,
)
from ska_tmc_common.dev_factory import DevFactory
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
    TIMEOUT,
    create_cm_no_faulty_devices,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invocation."""
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


@pytest.mark.SKA_low
def test_set_health_state_ok(tango_context):
    """Test set healthstate ok"""
    devFactory = DevFactory()
    proxy = devFactory.get_device(MCCS_MLN_DEVICE)
    proxy.SetMccsControllerAdminMode(AdminMode.ONLINE)
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, _input_parameter=InputParameterLow(None)
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
    proxy = devFactory.get_device(LOW_SDP_MASTER_DEVICE)
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


@pytest.mark.SKA_low
def test_set_health_state_degraded(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_degraded(devFactory, cm, 40)
    assert cm.component.telescope_health_state == HealthState.DEGRADED


def set_failed(devFactory, cm, expected_elapsed_time=1.5):
    proxy = devFactory.get_device(LOW_SDP_MASTER_DEVICE)
    proxy.SetDirectHealthState(HealthState.DEGRADED)
    assert proxy.HealthState == HealthState.DEGRADED
    proxy = devFactory.get_device(LOW_SUBARRAY_DEVICE)
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


@pytest.mark.SKA_low
def test_set_health_state_failed(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_failed(devFactory, cm, 40)
    assert cm.component.telescope_health_state == HealthState.FAILED


def set_device_unknown(devFactory, cm, expected_elapsed_time=12):
    proxy = devFactory.get_device(LOW_SDP_MASTER_DEVICE)
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


@pytest.mark.SKA_low
def test_set_health_state_unknown(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_unknown(devFactory, cm)
    assert cm.component.telescope_health_state == HealthState.UNKNOWN



from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.subarray import SKASubarray
import tango
import time
import pytest
from ska_tango_base.control_model import HealthState
from tests.settings import count_faulty_devices, logger, TIMEOUT
from test_cm_all_working import create_cm
from ska_tango_base.obs import SKAObsDevice
from tests.devices import HelperStateDevice
from ska_tmc_centralnode_mid.dev_factory import DevFactory

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": SKASubarray,
            "devices": [
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray02"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray03"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray02"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray03"
                }
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
                },
                {
                    "name": "ska_mid/tm_subarray_node/1"
                },
                {
                    "name": "ska_mid/tm_subarray_node/2"
                },
                {
                    "name": "ska_mid/tm_subarray_node/3"
                },
            ]
        }        
    )


def test_set_health_state_ok(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    # initially all devices are OK
    assert cm.component.telescope_health_state == HealthState.OK

def test_set_health_state_degraded(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    devFactory = DevFactory()
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
    assert elapsed_time < 1.5
    assert cm.component.telescope_health_state == HealthState.DEGRADED


def test_set_health_state_failed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    devFactory = DevFactory()
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
    assert elapsed_time < 1.5
    assert cm.component.telescope_health_state == HealthState.FAILED

def set_unknown(devFactory, dev_name):
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/1")
    proxy.SetDirectHealthState(HealthState.UNKNOWN)
    assert proxy.HealthState == HealthState.UNKNOWN

def test_set_health_state_unknown(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    devFactory = DevFactory()
    set_unknown(devFactory, "mid_csp/elt/master")
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
    assert elapsed_time < 1.5
    assert cm.component.telescope_health_state == HealthState.UNKNOWN
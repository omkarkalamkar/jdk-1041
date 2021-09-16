
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
                    "name": "ska_mid/tm_subarray_node/1"
                },
                {
                    "name": "ska_mid/tm_subarray_node/2"
                },
                {
                    "name": "ska_mid/tm_subarray_node/3"
                },
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
                }
            ]
        }        
    )


def test_aggregation_default(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0

    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    # import debugpy; debugpy.debug_this_thread()
    assert cm.component.telescope_state == tango.DevState.FAULT
    assert cm.component.tmc_op_state == tango.DevState.UNKNOWN
    assert cm.component.telescope_health_state == HealthState.OK
    
def test_telescope_state_on(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)

    devFactory = DevFactory()
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.TriggerStateChange("init_completed")
    proxy.TriggerStateChange("component_on")
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("mid_sdp/elt/master")
    proxy.TriggerStateChange("init_completed")
    proxy.TriggerStateChange("component_on")
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("mid_d0001/elt/master")
    proxy.TriggerStateChange("init_completed")
    proxy.TriggerStateChange("component_on")
    assert proxy.State() == tango.DevState.ON
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_state != tango.DevState.ON:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < 1.5
    assert cm.component.telescope_state == tango.DevState.ON
   

def test_telescope_state_off(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)

    devFactory = DevFactory()
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.TriggerStateChange("init_completed")
    proxy.TriggerStateChange("component_off")
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("mid_sdp/elt/master")
    proxy.TriggerStateChange("init_completed")
    proxy.TriggerStateChange("component_off")
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("mid_d0001/elt/master")
    proxy.TriggerStateChange("init_completed")
    proxy.TriggerStateChange("component_off")
    assert proxy.State() == tango.DevState.OFF
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_state != tango.DevState.OFF:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < 1.5
    assert cm.component.telescope_state == tango.DevState.OFF


def test_telescope_state_init(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)

    devFactory = DevFactory()
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.SetDirectState(tango.DevState.INIT)
    assert proxy.State() == tango.DevState.INIT
    proxy = devFactory.get_device("mid_sdp/elt/master")
    proxy.TriggerStateChange("init_completed")
    assert proxy.State() == tango.DevState.DISABLE
    proxy = devFactory.get_device("mid_d0001/elt/master")
    proxy.TriggerStateChange("init_completed")
    proxy.TriggerStateChange("component_off")
    assert proxy.State() == tango.DevState.OFF
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_state != tango.DevState.INIT:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < 1.5
    assert cm.component.telescope_state == tango.DevState.INIT

def test_telescope_state_fault_over_standby(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)

    devFactory = DevFactory()
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.SetDirectState(tango.DevState.FAULT)
    assert proxy.State() == tango.DevState.FAULT
    proxy = devFactory.get_device("mid_sdp/elt/master")
    proxy.SetDirectState(tango.DevState.STANDBY)
    assert proxy.State() == tango.DevState.STANDBY
    proxy = devFactory.get_device("mid_d0001/elt/master")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_state != tango.DevState.FAULT:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < 1.5
    assert cm.component.telescope_state == tango.DevState.FAULT

def test_telescope_state_standby(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)

    devFactory = DevFactory()
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.SetDirectState(tango.DevState.STANDBY)
    assert proxy.State() == tango.DevState.STANDBY
    proxy = devFactory.get_device("mid_sdp/elt/master")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("mid_d0001/elt/master")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_state != tango.DevState.STANDBY:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < 1.5
    assert cm.component.telescope_state == tango.DevState.STANDBY
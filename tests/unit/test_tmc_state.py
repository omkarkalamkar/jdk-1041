
from logging import debug, getLogger
from ska_tango_base.subarray import SKASubarray
import tango
import time
import pytest
from ska_tango_base.control_model import HealthState
from tests.settings import count_faulty_devices, logger, TIMEOUT
from test_cm_all_working import create_cm
from tests.helper_state_device import HelperStateDevice
from tests.helper_state_device_subarray import HelperSubarrayStateDevice
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from test_telescope_state_startup import create_cm_no_faulty_devices

logger = getLogger(__name__)

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": SKASubarray,
            "devices": [
                {
                    "name": "mid_csp/elt/master"
                },
                {
                    "name": "mid_sdp/elt/master"
                },
                {
                    "name": "mid_d0001/elt/master"
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
                    "name": "ska_mid/tm_leaf_node/sdp_master"
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
            ]
        }      
    )

def set_device_init(devFactory, cm, expected_elapsed_time):
    # import debugpy; debugpy.debug_this_thread()
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/1")
    proxy.SetDirectState(tango.DevState.INIT)
    assert proxy.State() == tango.DevState.INIT
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/2")
    proxy.SetDirectState(tango.DevState.DISABLE)
    assert proxy.State() == tango.DevState.DISABLE
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/3")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray01")
    proxy.SetDirectState(tango.DevState.INIT)
    assert proxy.State() == tango.DevState.INIT
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray02")
    proxy.SetDirectState(tango.DevState.INIT)
    assert proxy.State() == tango.DevState.INIT
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray03")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray01")
    proxy.SetDirectState(tango.DevState.INIT)
    assert proxy.State() == tango.DevState.INIT
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray02")
    proxy.SetDirectState(tango.DevState.DISABLE)
    assert proxy.State() == tango.DevState.DISABLE
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray03")
    proxy.SetDirectState(tango.DevState.INIT)
    assert proxy.State() == tango.DevState.INIT
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_master")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_master")
    proxy.SetDirectState(tango.DevState.INIT)
    assert proxy.State() == tango.DevState.INIT
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.tmc_op_state != tango.DevState.INIT:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time

def test_tmc_state_init(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_init(devFactory, cm, 5)
    assert cm.component.tmc_op_state == tango.DevState.INIT

def test_tmc_state_init_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_device_init(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.INIT

def test_tmc_state_init_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_device_init(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.INIT

def set_one_device_fault(devFactory, cm, expected_elapsed_time):
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/1")
    proxy.SetDirectState(tango.DevState.FAULT)
    assert proxy.State() == tango.DevState.FAULT
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/2")
    proxy.SetDirectState(tango.DevState.STANDBY)
    assert proxy.State() == tango.DevState.STANDBY
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/3")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray01")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray02")
    proxy.SetDirectState(tango.DevState.STANDBY)
    assert proxy.State() == tango.DevState.STANDBY
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray03")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray01")
    proxy.SetDirectState(tango.DevState.STANDBY)
    assert proxy.State() == tango.DevState.STANDBY
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray02")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray03")
    proxy.SetDirectState(tango.DevState.STANDBY)
    assert proxy.State() == tango.DevState.STANDBY
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_master")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_master")
    proxy.SetDirectState(tango.DevState.STANDBY)
    assert proxy.State() == tango.DevState.STANDBY
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.tmc_op_state != tango.DevState.FAULT:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time

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
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/1")
    proxy.SetDirectState(tango.DevState.STANDBY)
    assert proxy.State() == tango.DevState.STANDBY
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/2")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/3")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray01")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray02")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray03")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray01")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray02")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray03")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_master")
    proxy.SetDirectState(tango.DevState.OFF)
    assert proxy.State() == tango.DevState.OFF
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_master")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.tmc_op_state != tango.DevState.STANDBY:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time

def test_tmc_state_standby(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_device_standby(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.STANDBY

def test_tmc_state_standby_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_device_standby(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.STANDBY

def test_tmc_state_standby_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_device_standby(devFactory, cm, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.STANDBY

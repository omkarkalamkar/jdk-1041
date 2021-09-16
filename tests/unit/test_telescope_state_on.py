
from logging import debug
from ska_tango_base.subarray import SKASubarray
import tango
import time
import pytest
from ska_tango_base.control_model import HealthState
from tests.settings import count_faulty_devices, logger, TIMEOUT
from test_cm_all_working import create_cm
from test_telescope_state_startup import create_cm_no_faulty_devices
from tests.helper_state_device import HelperStateDevice
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

def set_devices_on(cm, devFactory, expected_elapsed_time):
    proxy = devFactory.get_device("mid_csp/elt/master")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("mid_sdp/elt/master")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("mid_d0001/elt/master")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_state != tango.DevState.ON:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time

def test_telescope_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.telescope_state == tango.DevState.ON

def test_telescope_state_on_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.telescope_state == tango.DevState.ON

def test_telescope_state_on_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.telescope_state == tango.DevState.ON

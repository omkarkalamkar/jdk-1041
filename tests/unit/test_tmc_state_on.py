import time
from logging import debug

import pytest
import tango
from ska_tango_base.control_model import HealthState
from ska_tango_base.subarray import SKASubarray
from test_cm_all_working import create_cm
from test_telescope_startup import create_cm_no_faulty_devices

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import TIMEOUT, count_faulty_devices, logger


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


def set_devices_on(cm, devFactory, expected_elapsed_time):
    proxy = devFactory.get_device("ska_mid/tm_subarray_node/1")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_subarray01")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_subarray01")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/csp_master")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/sdp_master")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    proxy = devFactory.get_device("ska_mid/tm_leaf_node/d0001")
    proxy.SetDirectState(tango.DevState.ON)
    assert proxy.State() == tango.DevState.ON
    # wait for the propagations by event or polling
    start_time = time.time()
    elapsed_time = 0
    while cm.component.tmc_op_state != tango.DevState.ON:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time


def test_tmc_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.ON


def test_tmc_state_on_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.ON


def test_tmc_state_on_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.ON

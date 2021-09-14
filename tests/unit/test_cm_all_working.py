import pytest
import logging
import time
from ska_tango_base.control_model import HealthState

from ska_tango_base.obs.obs_device import SKAObsDevice
import tango
from ska_tmc_centralnode_mid.model.component import SubArrayDeviceInfo
from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.manager.component_manager import CNComponentManager
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel
from ska_tango_base.subarray import SKASubarray
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.settings import DEVICE_LIST, SLEEP_TIME, TIMEOUT, logger, DishLeafNodePrefix, NumDishes

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
            "class": SKAObsDevice,
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
                }
            ]
        }
    )

def count_faulty_devices(cm):
    result = 0
    for devInfo in cm.devices:
        if devInfo.faulty:
            result += 1
    return result

def create_cm():
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(op_state_model, logger=logger)
    for dev in DEVICE_LIST:
        cm.add_device(dev)
    start_time = time.time()
    num_devices = len(DEVICE_LIST)
    while num_devices != len(cm.checked_devices):
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    
    return cm, start_time

def test_all_working(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0

    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    for devInfo in cm.devices:
        assert not devInfo.faulty
        if "subarray" in devInfo.dev_name.lower():
            assert isinstance(devInfo, SubArrayDeviceInfo)

def test_aggregation(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0

    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    # import debugpy; debugpy.debug_this_thread()
    assert cm.component.telescope_state == tango.DevState.UNKNOWN
    assert cm.component.tmc_op_state == tango.DevState.UNKNOWN
    assert cm.component.telescope_health_state == HealthState.OK
    
    


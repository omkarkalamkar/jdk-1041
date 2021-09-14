import pytest
import logging
import time
from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.manager.component_manager import CNComponentManager
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel
from ska_tango_base.subarray import SKASubarray
from tests.settings import DEVICE_LIST, SLEEP_TIME, TIMEOUT, logger, DishLeafNodePrefix, NumDishes

WORKING_DEVICES = 9

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": CentralNode,
            "devices": [
                {
                    "name": "ska_mid/tm_central/central_node"
                }
            ],
        },
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
        }
    )

def count_faulty_devices(cm):
    result = 0
    for devInfo in cm.devices:
        if devInfo.faulty:
            result += 1
    return result

def test_some_working_other_faulty(tango_context):
    logger.info("%s", tango_context)
    
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(op_state_model, logger=logger)
    cm.add_dishes(DishLeafNodePrefix, NumDishes)
    for dev in DEVICE_LIST:
        cm.add_device(dev)
    start_time = time.time()
    num_faulty = count_faulty_devices(cm)
    num_devices = len(DEVICE_LIST) + NumDishes
    while num_devices != len(cm.checked_devices):
        logger.info("Faulty devices %s", num_faulty)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        num_faulty = count_faulty_devices(cm)
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    assert num_faulty == num_devices - WORKING_DEVICES

import pytest
import logging
import time

from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.manager.component_manager import CNComponentManager
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel
from ska_tango_base.subarray import SKASubarray
from tests.settings import DEVICE_LIST, SLEEP_TIME, TIMEOUT, logger, DishLeafNodePrefix, NumDishes

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": SKABaseDevice,
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
            ],
        }
    )

def count_faulty_devices(cm):
    result = 0
    for devInfo in cm.devices:
        if devInfo.faulty:
            result += 1
    return result

def test_one_working_other_faulty(tango_context):
    logger.info("%s", tango_context)
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(op_state_model, logger=logger)
    cm.add_dishes(DishLeafNodePrefix, NumDishes)
    for dev in DEVICE_LIST:
        cm.add_device(dev)
    start_time = time.time()
    num_faulty = count_faulty_devices(cm)
    while num_faulty != len(cm.devices)-1:
        logger.info("Faulty devices %s", num_faulty)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        num_faulty = count_faulty_devices(cm)
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    subarrayDevInfo = cm.get_device("ska_mid/tm_subarray_node/1")
    for devInfo in cm.devices:
        if devInfo == subarrayDevInfo:
            assert not devInfo.faulty
        else:
            assert devInfo.faulty


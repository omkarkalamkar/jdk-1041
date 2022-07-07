import time

import pytest
from ska_tango_base.base.base_device import SKABaseDevice

from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    DEVICE_LIST_MID,
    SLEEP_TIME,
    TIMEOUT,
    DishLeafNodePrefix,
    NumDishes,
    count_faulty_devices,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": SKABaseDevice,
            "devices": [{"name": "ska_mid/tm_central/central_node"}],
        },
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": "ska_mid/tm_subarray_node/1"},
            ],
        },
    )


@pytest.mark.cn_cm
def test_one_working_other_faulty(tango_context):
    logger.info("%s", tango_context)
    # op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(
        logger=logger, _input_parameter=InputParameterMid(None)
    )
    cm.add_dishes(DishLeafNodePrefix, NumDishes)
    for dev in DEVICE_LIST_MID:
        cm.add_device(dev)
    start_time = time.time()
    num_faulty = count_faulty_devices(cm)
    while num_faulty != len(cm.devices) - 1:
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
            assert not devInfo.unresponsive
        else:
            assert devInfo.unresponsive

import time

import pytest

from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.settings import (
    DEVICE_LIST_MID,
    SLEEP_TIME,
    TIMEOUT,
    DishLeafNodePrefix,
    NumDishes,
    count_faulty_devices,
    logger,
)


@pytest.mark.refactor_telescopeon
def test_all_devices_faulty():
    cm = CNComponentManager(
        logger=logger, _input_parameter=InputParameterMid(None)
    )
    cm.add_dishes(DishLeafNodePrefix, NumDishes)
    cm.add_multiple_devices(DEVICE_LIST_MID)
    start_time = time.time()
    num_faulty = count_faulty_devices(cm)
    while num_faulty != len(cm.devices):
        logger.info("Faulty devices %s", num_faulty)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        num_faulty = count_faulty_devices(cm)
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    for devInfo in cm.devices:
        assert devInfo.unresponsive

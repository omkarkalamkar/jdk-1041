import time

import pytest

from ska_tmc_centralnode_mid.manager.component_manager import (
    CNComponentManager,
)
from ska_tmc_centralnode_mid.model.input import InputParameterLow
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel
from tests.settings import (
    DEVICE_LIST_LOW,
    SLEEP_TIME,
    TIMEOUT,
    count_faulty_devices,
    logger,
)


def test_all_low_devices_faulty():
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(
        op_state_model, _input_parameter=InputParameterLow(None), logger=logger
    )
    cm.add_multiple_devices(DEVICE_LIST_LOW)
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

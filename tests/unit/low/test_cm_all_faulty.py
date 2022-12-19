import time

import pytest
from ska_tmc_common.op_state_model import TMCOpStateModel
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)

from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    DEVICE_LIST_LOW,
    SLEEP_TIME,
    TIMEOUT,
    count_faulty_devices,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/csp_master"},
                {"name": "low-csp/control/0"},
                {"name": "ska_low/tm_leaf_node/sdp_master"},
                {"name": "low-sdp/control/0"},
            ],
        },
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": "ska_low/tm_subarray_node/1"},
            ],
        },
    )


def test_all_low_devices_faulty():
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(
        op_state_model,
        _input_parameter=InputParameterLow(None),
        logger=logger,
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

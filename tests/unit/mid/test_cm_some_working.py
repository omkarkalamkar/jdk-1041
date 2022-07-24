import time

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

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

WORKING_DEVICES = 3


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
                {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
                {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
            ],
        },
    )


@pytest.mark.refactor_telescopeon
@pytest.mark.skip
def test_some_working_other_faulty(tango_context):
    logger.info("%s", tango_context)

    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(
        op_state_model, _input_parameter=InputParameterMid(None), logger=logger
    )
    cm.add_dishes(DishLeafNodePrefix, NumDishes)
    for dev in DEVICE_LIST_MID:
        cm.add_device(dev)
    start_time = time.time()
    num_faulty = count_faulty_devices(cm)
    # the device list contains one duplicate of the dishes
    num_devices = len(DEVICE_LIST_MID) + NumDishes - 1
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

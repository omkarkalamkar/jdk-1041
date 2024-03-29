"""Test case for cm all faulty"""
import time

import pytest
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    DEVICE_LIST_LOW,
    SLEEP_TIME,
    TIMEOUT,
    count_faulty_devices,
    logger,
)

# from ska_tmc_common.test_helpers.helper_subarray_device import (
#     HelperSubArrayDevice,
# )


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invokation"""
    return (
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": "a/b/c"},
            ],
        },
    )


@pytest.mark.test
@pytest.mark.SKA_low
def test_all_low_devices_faulty(tango_context):
    """Test all low devices faulty"""
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerLow(
        op_state_model,
        _input_parameter=InputParameterLow(None),
        logger=logger,
    )
    cm.add_multiple_devices(DEVICE_LIST_LOW)
    start_time = time.time()
    num_faulty = count_faulty_devices(cm)
    logger.info(f"Component manager faulty devices{cm.checked_devices}")
    logger.info(f"Component total devices{cm.devices}")
    while num_faulty != len(cm.devices):
        logger.info(f"Number of devices {len(cm.devices)}")
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

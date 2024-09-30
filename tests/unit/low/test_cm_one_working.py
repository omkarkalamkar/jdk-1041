"""Test case module"""
import time

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DEVICE_LIST_LOW,
    LOW_SUBARRAY_DEVICE,
    SLEEP_TIME,
    TIMEOUT,
    count_faulty_devices,
    logger,
    set_devices_unresponsive,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invocation"""
    return (
        {
            "class": SKABaseDevice,
            "devices": [{"name": "ska_low/tm_central/central_node"}],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
            ],
        },
    )


FAULTY_LIST = [
    "ska_low/tm_leaf_node/mccs_master",
    "low-mccs/control/control",
    "low-sdp/control/0",
    "low-csp/control/0",
    "ska_low/tm_leaf_node/csp_master",
    "ska_low/tm_leaf_node/sdp_master",
    "ska_low/tm_leaf_node/csp_subarray01",
    "ska_low/tm_leaf_node/sdp_subarray01",
]


@pytest.mark.SKA_low
def test_low_one_working_other_faulty(
    tango_context,
):
    """Test low one working other faulty devices"""
    logger.info("%s", tango_context)
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerLow(
        op_state_model, _input_parameter=InputParameterLow(None), logger=logger
    )

    for dev in DEVICE_LIST_LOW:
        cm.add_device(dev)
    set_devices_unresponsive(cm, FAULTY_LIST)
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
    subarrayDevInfo = cm.get_device("ska_low/tm_subarray_node/1")
    for devInfo in cm.devices:
        if devInfo == subarrayDevInfo:
            assert not devInfo.unresponsive
        else:
            assert devInfo.unresponsive

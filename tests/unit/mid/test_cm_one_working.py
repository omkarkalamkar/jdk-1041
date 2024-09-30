"""Test cases file"""
import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DEVICE_LIST_MID,
    DISH_LEAF_NODE_PREFIX,
    MID_SUBARRAY_DEVICE,
    NUM_DISHES,
    logger,
    set_devices_unresponsive,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": SKABaseDevice,
            "devices": [{"name": "ska_mid/tm_central/central_node"}],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
            ],
        },
    )


FAULTY_LIST = [
    "ska_mid/tm_leaf_node/csp_master",
    "mid-csp/control/0",
    "ska_mid/tm_leaf_node/sdp_master",
    "mid-sdp/control/0",
    "ska_mid/tm_leaf_node/csp_subarray01",
    "ska_mid/tm_leaf_node/sdp_subarray01",
    "ska_mid/tm_leaf_node/d0001",
    "ska001/elt/master",
]


def test_one_working_other_faulty(tango_context):
    """Test with one working and other faulty devices"""
    logger.info("%s", tango_context)
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerMid(
        op_state_model, logger=logger, _input_parameter=InputParameterMid(None)
    )
    cm.add_dishes(DISH_LEAF_NODE_PREFIX, NUM_DISHES)
    for dev in DEVICE_LIST_MID:
        cm.add_device(dev)

    set_devices_unresponsive(cm, FAULTY_LIST)

    subarrayDevInfo = cm.get_device("ska_mid/tm_subarray_node/1")
    for devInfo in cm.devices:
        if devInfo == subarrayDevInfo:
            assert not devInfo.unresponsive
        else:
            assert devInfo.unresponsive

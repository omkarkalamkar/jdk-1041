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
    MID_CSP_SLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    NUM_DISHES,
    count_faulty_devices,
    logger,
    set_devices_unresponsive,
)

WORKING_DEVICES = 3


@pytest.fixture()
def devices_to_load():
    """devices to load for command invokation"""
    return (
        {
            "class": SKABaseDevice,
            "devices": [{"name": "mid-tmc/central-node/0"}],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
    )


FAULTY_LIST = [
    "ska_mid/tm_leaf_node/csp_master",
    "mid-csp/control/0",
    "ska_mid/tm_leaf_node/sdp_master",
    "mid-sdp/control/0",
    "ska_mid/tm_leaf_node/d0001",
    "ska001/elt/master",
]


def test_some_working_other_faulty(tango_context):
    """Test with some working and some faulty devices"""
    logger.info("%s", tango_context)

    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerMid(
        op_state_model,
        _input_parameter=InputParameterMid(None),
        logger=logger,
    )
    dishes = cm.add_dishes(DISH_LEAF_NODE_PREFIX, NUM_DISHES)
    for dev in DEVICE_LIST_MID:
        cm.add_device(dev)
    set_devices_unresponsive(cm, FAULTY_LIST)
    set_devices_unresponsive(cm, dishes)

    num_faulty = count_faulty_devices(cm)
    # the device list contains one duplicate of the dishes
    num_devices = len(DEVICE_LIST_MID) + NUM_DISHES - 1

    assert num_faulty == num_devices - WORKING_DEVICES

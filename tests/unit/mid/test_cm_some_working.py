"""Test cases file"""

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice

from ska_tmc_centralnode.utils.constants import CENTRALNODE_MID
from tests.settings import (
    DEVICE_LIST_MID,
    DISH_LEAF_NODE_DEVICE,
    DISH_LEAF_NODE_DEVICE_099,
    DISH_LEAF_NODE_DEVICE_500,
    DISH_LEAF_NODE_DEVICE_999,
    DISH_LEAF_NODE_PREFIX,
    DISH_MASTER_DEVICE,
    DISH_MASTER_DEVICE_099,
    DISH_MASTER_DEVICE_500,
    DISH_MASTER_DEVICE_999,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    NUM_DISHES,
    count_faulty_devices,
    create_cm,
    set_devices_unresponsive,
)

WORKING_DEVICES = 3


@pytest.fixture()
def devices_to_load():
    """devices to load for command invokation"""
    return (
        {
            "class": SKABaseDevice,
            "devices": [{"name": CENTRALNODE_MID}],
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
    MID_CSP_MLN_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISH_MASTER_DEVICE_999,
    DISH_LEAF_NODE_DEVICE_099,
    DISH_LEAF_NODE_DEVICE_999,
    DISH_LEAF_NODE_DEVICE_500,
    DISH_MASTER_DEVICE_099,
    DISH_MASTER_DEVICE_500,
]


def mock_callback(*args, **kwargs):
    """Devices to mock_callback"""


def test_some_working_other_faulty(tango_context):
    """Test with some working and some faulty devices"""

    cm, _ = create_cm(True, True)

    dishes = cm.add_dishes(DISH_LEAF_NODE_PREFIX, NUM_DISHES)
    for dev in DEVICE_LIST_MID:
        cm.add_device(dev)

    set_devices_unresponsive(cm, FAULTY_LIST)
    set_devices_unresponsive(cm, dishes)

    num_faulty = count_faulty_devices(cm)
    # the device list contains one duplicate of the dishes
    num_devices = len(DEVICE_LIST_MID) + NUM_DISHES - 1

    assert num_faulty == num_devices - WORKING_DEVICES

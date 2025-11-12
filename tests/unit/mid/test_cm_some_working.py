"""Test cases file"""

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice

from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.input import InputParameterMid
from ska_tmc_centralnode.utils.constants import CENTRALNODE_MID
from tests.settings import (
    DEVICE_LIST_MID,
    DISH_LEAF_NODE_DEVICE,
    DISH_LEAF_NODE_PREFIX,
    DISH_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    NUM_DISHES,
    count_faulty_devices,
    dish_vcc_process_callback,
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
]


def mock_callback(*args, **kwargs):
    """Devices to mock_callback"""


def test_some_working_other_faulty(tango_context):
    """Test with some working and some faulty devices"""
    logger.info("%s", tango_context)

    op_state_model = TMCOpStateModel(logger)

    cm = CNComponentManagerMid(
        op_state_model,
        _dish_vcc_command_status_callback=dish_vcc_process_callback,
        _input_parameter=InputParameterMid(None),
        logger=logger,
        _update_device_callback=mock_callback,
        _update_telescope_state_callback=mock_callback,
        _update_telescope_health_state_callback=mock_callback,
        _update_tmc_op_state_callback=mock_callback,
        _update_imaging_callback=mock_callback,
        _telescope_availability_callback=mock_callback,
        _update_dishvccconfig_callback=mock_callback,
        _dishvccvalidation_callback=mock_callback,
        default_array_layout_source_uris=[
            "gitlab://gitlab.com/ska-telescope/"
            + "ska-telmodel-data?main#tmdata"
        ],
        default_array_layout_path=(
            "instrument/ska1_mid/layout/mid-layout.json"
        ),
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

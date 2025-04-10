"""Test cases file"""
import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.input import InputParameterMid
from ska_tmc_centralnode.utils.constants import CENTRALNODE_MID
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
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
    dish_vcc_process_callback,
    logger,
    set_devices_unresponsive,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": SKABaseDevice,
            "devices": [{"name": CENTRALNODE_MID}],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
            ],
        },
    )


FAULTY_LIST = [
    MID_CSP_MLN_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
]


def mock_callback(*args, **kwargs):
    """Devices to mock_callback"""


def test_one_working_other_faulty(tango_context):
    """Test with one working and other faulty devices"""
    logger.info("%s", tango_context)
    op_state_model = TMCOpStateModel(logger)

    cm = CNComponentManagerMid(
        op_state_model,
        _input_parameter=InputParameterMid(None),
        logger=logger,
        _dish_vcc_command_status_callback=dish_vcc_process_callback,
        _update_device_callback=mock_callback,
        _update_telescope_state_callback=mock_callback,
        _update_telescope_health_state_callback=mock_callback,
        _update_tmc_op_state_callback=mock_callback,
        _update_imaging_callback=mock_callback,
        _telescope_availability_callback=mock_callback,
        _update_dishvccconfig_callback=mock_callback,
        _dishvccvalidation_callback=mock_callback,
    )

    dishes = cm.add_dishes(DISH_LEAF_NODE_PREFIX, NUM_DISHES)
    for dev in DEVICE_LIST_MID:
        cm.add_device(dev)

    set_devices_unresponsive(cm, FAULTY_LIST)
    set_devices_unresponsive(cm, dishes)
    subarrayDevInfo = cm.get_device(MID_SUBARRAY_DEVICE)
    for devInfo in cm.devices:
        if devInfo == subarrayDevInfo:
            assert not devInfo.unresponsive
        else:
            assert devInfo.unresponsive

"""Test cases file for component manager faulty"""
import pytest
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.settings import (
    DEVICE_LIST_MID,
    DISH_LEAF_NODE_PREFIX,
    NUM_DISHES,
    logger,
    set_devices_unresponsive,
)


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


def test_all_devices_faulty(tango_context):
    """Test with all devices faulty"""
    logger.info("%s", tango_context)
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerMid(
        op_state_model,
        _input_parameter=InputParameterMid(None),
        logger=logger,
    )
    cm.add_dishes(DISH_LEAF_NODE_PREFIX, NUM_DISHES)
    cm.add_multiple_devices(DEVICE_LIST_MID)
    set_devices_unresponsive(cm, DEVICE_LIST_MID)
    logger.info(f"Component manager faulty devices{cm.checked_devices}")
    logger.info(f"Component total devices{cm.devices}")

    for devInfo in cm.devices:
        assert devInfo.unresponsive

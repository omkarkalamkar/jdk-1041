"""Test cases file for component manager faulty"""

from unittest.mock import Mock

import pytest
from ska_tmc_common.op_state_model import TMCOpStateModel
from ska_tmc_simulators import HelperBaseDevice

from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.settings import (
    DEVICE_LIST_MID,
    DISH_LEAF_NODE_PREFIX,
    NUM_DISHES,
    dish_vcc_process_callback,
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


def mock_callback(*args, **kwargs):
    """Devices to mock_callback"""


def test_all_devices_faulty(tango_context):
    """Test with all devices faulty"""
    op_state_model = TMCOpStateModel(logger)

    default_array_layout_url = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/"
            "ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": "instrument/ska1_mid/layout/mid-layout.json",
    }

    mock_array_layout_callback = Mock()

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
        array_layout_url_callback=mock_array_layout_callback,
        default_array_layout_url_callback=mock_array_layout_callback,
        _update_dishvccconfig_callback=mock_callback,
        _dishvccvalidation_callback=mock_callback,
        default_array_layout_url=default_array_layout_url,
    )

    dishes = cm.add_dishes(DISH_LEAF_NODE_PREFIX, NUM_DISHES)
    cm.add_multiple_devices(DEVICE_LIST_MID)
    set_devices_unresponsive(cm, DEVICE_LIST_MID)
    set_devices_unresponsive(cm, dishes)

    logger.info(f"Component manager faulty devices{len(cm.checked_devices)}")
    logger.info(f"Component total devices{cm.devices}")

    for devInfo in cm.devices:
        logger.info(devInfo.dev_name)
        assert devInfo.unresponsive

"""Test cases file for component manager faulty"""

import pytest
from ska_tmc_simulators import HelperBaseDevice

from tests.settings import (
    DEVICE_LIST_MID,
    DISH_LEAF_NODE_PREFIX,
    NUM_DISHES,
    create_cm,
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

    cm, _ = create_cm(True, True)

    dishes = cm.add_dishes(DISH_LEAF_NODE_PREFIX, NUM_DISHES)
    cm.add_multiple_devices(DEVICE_LIST_MID)
    set_devices_unresponsive(cm, DEVICE_LIST_MID)
    set_devices_unresponsive(cm, dishes)

    logger.info(f"Component manager faulty devices{len(cm.checked_devices)}")
    logger.info(f"Component total devices{cm.devices}")

    for dev_info in cm.devices:
        logger.info(dev_info.dev_name)
        assert dev_info.unresponsive

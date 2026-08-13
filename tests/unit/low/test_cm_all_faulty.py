"""Test case for cm all faulty"""

import pytest
from ska_tmc_simulators import HelperBaseDevice

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    DEVICE_LIST_LOW,
    create_cm,
    logger,
    set_devices_unresponsive,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invocation"""
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


@pytest.mark.SKA_low
def test_all_low_devices_faulty(tango_context):
    """Test all low devices faulty"""
    cm, _ = create_cm(True, True, InputParameterLow(None))
    cm.add_multiple_devices(DEVICE_LIST_LOW)
    set_devices_unresponsive(cm, DEVICE_LIST_LOW)

    logger.info(f"Component manager faulty devices{cm.checked_devices}")
    logger.info(f"Component total devices{cm.devices}")

    for devInfo in cm.devices:
        assert devInfo.unresponsive

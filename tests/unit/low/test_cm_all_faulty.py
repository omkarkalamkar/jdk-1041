"""Test case for cm all faulty"""


import pytest
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import DEVICE_LIST_LOW, logger, set_devices_unresponsive


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


@pytest.mark.test_all_low_devices_faulty
@pytest.mark.SKA_low
def test_all_low_devices_faulty(tango_context):
    """Test all low devices faulty"""
    op_state_model = TMCOpStateModel(logger)

    cm = CNComponentManagerLow(
        op_state_model,
        _input_parameter=InputParameterLow(None),
        logger=logger,
        _update_device_callback=mock_callback,
        _update_telescope_state_callback=mock_callback,
        _update_telescope_health_state_callback=mock_callback,
        _update_tmc_op_state_callback=mock_callback,
        _update_imaging_callback=mock_callback,
        _telescope_availability_callback=mock_callback,
    )

    cm.add_multiple_devices(DEVICE_LIST_LOW)
    set_devices_unresponsive(cm, DEVICE_LIST_LOW)

    logger.info(f"Component manager faulty devices{cm.checked_devices}")
    logger.info(f"Component total devices{cm.devices}")

    for devInfo in cm.devices:
        assert devInfo.unresponsive

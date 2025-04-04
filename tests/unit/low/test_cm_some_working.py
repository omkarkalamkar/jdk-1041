"""Test case module"""

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SUBARRAY_LN,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SUBARRAY_LN,
)
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DEVICE_LIST_LOW,
    LOW_SUBARRAY_DEVICE,
    count_faulty_devices,
    logger,
    set_devices_unresponsive,
)

WORKING_DEVICES = 5


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invocation"""
    return (
        {
            "class": SKABaseDevice,
            "devices": [{"name": CENTRALNODE_LOW}],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
            ],
        },
    )


FAULTY_LIST = [
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_CSP_SUBARRAY_LN,
    LOW_SDP_SUBARRAY_LN,
]


def mock_callback(*args, **kwargs):
    """Devices to mock_callback"""


@pytest.mark.test_low_some_working_other_faulty
@pytest.mark.SKA_low
def test_low_some_working_other_faulty(tango_context):
    """Test low some working other faulty devices."""
    logger.info("%s", tango_context)
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
        communication_state_callback=mock_callback,
        component_state_callback=mock_callback,
    )

    for dev in DEVICE_LIST_LOW:
        cm.add_device(dev)
    set_devices_unresponsive(cm, FAULTY_LIST)
    num_faulty = count_faulty_devices(cm)
    num_devices = len(DEVICE_LIST_LOW)
    assert num_faulty == num_devices - WORKING_DEVICES

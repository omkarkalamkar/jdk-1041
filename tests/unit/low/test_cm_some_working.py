"""Test case module"""

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow
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
            "devices": [{"name": "ska_low/tm_central/central_node"}],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
            ],
        },
    )


FAULTY_LIST = [
    "ska_low/tm_leaf_node/csp_master",
    "ska_low/tm_leaf_node/sdp_master",
    "ska_low/tm_leaf_node/csp_subarray01",
    "ska_low/tm_leaf_node/sdp_subarray01",
]


@pytest.mark.SKA_low
def test_low_some_working_other_faulty(tango_context):
    """Test low some working other faulty devices."""
    logger.info("%s", tango_context)
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerLow(
        op_state_model, _input_parameter=InputParameterLow(None), logger=logger
    )
    for dev in DEVICE_LIST_LOW:
        cm.add_device(dev)
    set_devices_unresponsive(cm, FAULTY_LIST)
    num_faulty = count_faulty_devices(cm)
    num_devices = len(DEVICE_LIST_LOW)
    assert num_faulty == num_devices - WORKING_DEVICES

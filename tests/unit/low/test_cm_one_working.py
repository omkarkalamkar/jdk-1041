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
    logger,
    set_devices_unresponsive,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invocation"""
    return (
        {
            "class": SKABaseDevice,
            "devices": [{"name": "low-tmc/central-node/0"}],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
            ],
        },
    )


FAULTY_LIST = [
    "low-tmc/leaf-node-mccs/0",
    "low-mccs/control/control",
    "low-sdp/control/0",
    "low-csp/control/0",
    "low-tmc/leaf-node-csp/0",
    "low-tmc/leaf-node-sdp/0",
    "low-tmc/subarray-leaf-node-csp/01",
    "low-tmc/subarray-leaf-node-sdp/01",
]


@pytest.mark.SKA_low
def test_low_one_working_other_faulty(
    tango_context,
):
    """Test low one working other faulty devices"""
    logger.info("%s", tango_context)
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManagerLow(
        op_state_model, _input_parameter=InputParameterLow(None), logger=logger
    )

    for dev in DEVICE_LIST_LOW:
        cm.add_device(dev)
    set_devices_unresponsive(cm, FAULTY_LIST)

    subarrayDevInfo = cm.get_device("low-tmc/subarray/01")
    for devInfo in cm.devices:
        if devInfo == subarrayDevInfo:
            assert not devInfo.unresponsive
        else:
            assert devInfo.unresponsive

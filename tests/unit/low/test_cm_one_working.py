"""Test case module"""


import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice

from ska_tmc_centralnode.model.input import InputParameterLow
from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SUBARRAY_LN,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SUBARRAY_LN,
    MCCS_MASTER_DEVICE,
    MCCS_MLN_DEVICE,
)
from tests.settings import (
    DEVICE_LIST_LOW,
    LOW_SUBARRAY_DEVICE,
    create_cm,
    set_devices_unresponsive,
)


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
    MCCS_MLN_DEVICE,
    MCCS_MASTER_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_CSP_SUBARRAY_LN,
    LOW_SDP_SUBARRAY_LN,
]


def mock_callback(*args, **kwargs):
    """Devices to mock_callback"""


@pytest.mark.SKA_low
def test_low_one_working_other_faulty(
    tango_context,
):
    """Test low one working other faulty devices"""

    cm, _ = create_cm(True, True, InputParameterLow(None))

    for dev in DEVICE_LIST_LOW:
        cm.add_device(dev)
    set_devices_unresponsive(cm, FAULTY_LIST)

    subarrayDevInfo = cm.get_device("low-tmc/subarray/01")
    for dev_info in cm.devices:
        if dev_info == subarrayDevInfo:
            assert not dev_info.unresponsive
        else:
            assert dev_info.unresponsive

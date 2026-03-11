"""Test cases file component manager"""

import time

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.device_info import SubArrayDeviceInfo
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice

from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    count_faulty_devices,
    create_cm,
    logger,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invokations."""
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_SDP_MLN_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
                {"name": DISH_MASTER_DEVICE},
            ],
        },
    )


def test_all_working(tango_context):
    """Test all working"""
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0

    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    for devInfo in cm.devices:
        assert not devInfo.unresponsive
        if all(
            dev_name.lower() in devInfo.dev_name.lower()
            for dev_name in cm.input_parameter.subarray_dev_names
        ) and isinstance(devInfo, SubArrayDeviceInfo):
            assert isinstance(devInfo, SubArrayDeviceInfo)

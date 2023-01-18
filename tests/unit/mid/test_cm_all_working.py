import time

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.device_info import SubArrayDeviceInfo
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)

from tests.settings import (
    MID_SUBARRAY_DEVICE,
    count_faulty_devices,
    create_cm,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
                {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
                {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
            ],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "mid-csp/control/0"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "mid-sdp/control/0"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
                {"name": "mid_d0001/elt/master"},
            ],
        },
    )


def test_all_working(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0

    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    for devInfo in cm.devices:
        assert not devInfo.unresponsive
        if "subarray" in devInfo.dev_name.lower():
            assert isinstance(devInfo, SubArrayDeviceInfo)

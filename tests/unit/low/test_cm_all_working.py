import time

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.device_info import SubArrayDeviceInfo
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)
from ska_tmc_common.test_helpers.helper_subarray_leaf_device import (
    HelperSubarrayLeafDevice,
)

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import count_faulty_devices, create_cm, logger


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperMCCSStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
                {"name": "low-mccs/control/control"},
            ],
        },
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": "ska_low/tm_subarray_node/1"},
            ],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/csp_master"},
                {"name": "low_csp/elt/master"},
                {"name": "ska_low/tm_leaf_node/sdp_master"},
                {"name": "low_sdp/elt/master"},
            ],
        },
        {
            "class": HelperSubarrayLeafDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_subarray01"},
                {"name": "ska_low/tm_leaf_node/csp_subarray01"},
                {"name": "ska_low/tm_leaf_node/sdp_subarray01"},
            ],
        },
    )


def test_all_working(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0

    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    for devInfo in cm.devices:
        assert not devInfo.unresponsive
        if "subarray" in devInfo.dev_name.lower():
            assert isinstance(devInfo, SubArrayDeviceInfo)

import json
import time
import logging

import pytest
from ska_tmc_common.dev_factory import DevFactory
from tango.test_context import MultiDeviceTestContext
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice
# from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
#     HelperMCCSStateDevice,
# )

from ska_tmc_centralnode.central_node_mid import CentralNodeMid
from ska_tmc_centralnode.central_node_low import CentralNodeLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import SLEEP_TIME, TIMEOUT, logger

pytest.event_arrived = False


@pytest.fixture
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": "ska_mid/tm_subarray_node/1"},
                {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
                {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
                {"name": "ska_low/tm_leaf_node/csp_subarray01"},
                {"name": "ska_low/tm_leaf_node/sdp_subarray01"},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "mid-csp/control/0"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "mid-sdp/control/0"},
                {"name": "mid_d0001/elt/master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
                {"name": "ska_low/tm_subarray_node/1"},
                # {"name": "ska_low/tm_leaf_node/mccs_subarray01"},
                {"name": "ska_low/tm_leaf_node/csp_master"},
                {"name": "low-csp/control/0"},
                {"name": "ska_low/tm_leaf_node/sdp_master"},
                {"name": "low-sdp/control/0"},
            ],
        },
        # {
        #     "class": HelperMCCSStateDevice,
        #     "devices": [
        #         {"name": "ska_low/tm_leaf_node/mccs_master"},
        #         {"name": "low-mccs/control/control"},
        #     ],
        # },
        {
            "class": CentralNodeMid,
            "devices": [
                {
                    "name": "ska_mid/tm_central/central_node",
                    "properties": {
                        "CspMasterLeafNodeFQDN": [
                            "ska_mid/tm_leaf_node/csp_master"
                        ],
                        "CspMasterFQDN": ["mid-csp/control/0"],
                        "SdpMasterLeafNodeFQDN": [
                            "ska_mid/tm_leaf_node/sdp_master"
                        ],
                        "SdpMasterFQDN": ["mid-sdp/control/0"],
                        "DishLeafNodePrefix": ["ska_mid/tm_leaf_node/d"],
                        "TMMidSubarrayNodes": ["ska_mid/tm_subarray_node/1"],
                        "TMMidCspSubarrayLeafNodes": [
                            "ska_mid/tm_leaf_node/csp_subarray01"
                        ],
                        "TMMidSdpSubarrayLeafNodes": [
                            "ska_mid/tm_leaf_node/sdp_subarray01"
                        ],
                        "NumDishes": [1],
                    },
                }
            ],
        },
        {
            "class": CentralNodeLow,
            "devices": [
                {
                    "name": "ska_low/tm_central/central_node",
                    "properties": {
                        "CspMasterLeafNodeFQDN": [
                            "ska_low/tm_leaf_node/csp_master"
                        ],
                        "CspMasterFQDN": ["low-csp/control/0"],
                        "SdpMasterLeafNodeFQDN": [
                            "ska_low/tm_leaf_node/sdp_master"
                        ],
                        "SdpMasterFQDN": ["low-sdp/control/0"],
                        "TMLowSubarrayNodes": ["ska_low/tm_subarray_node/1"],
                        "TMLowCspSubarrayLeafNodes": [
                            "ska_low/tm_leaf_node/csp_subarray01"
                        ],
                        "TMLowSdpSubarrayLeafNodes": [
                            "ska_low/tm_leaf_node/sdp_subarray01"
                        ],
                    },
                }
            ],
        },
    )

@pytest.fixture
def tango_context(devices_to_load, request):
    true_context = request.config.getoption("--true-context")
    logging.info("true context: %s", true_context)
    if not true_context:
        with MultiDeviceTestContext(devices_to_load, process=False) as context:
            DevFactory._test_context = context
            logging.info("test context set")
            yield context
    else:
        yield None


def checked_devices(json_model):
    result = 0
    for dev in json_model["devices"]:
        if int(dev["ping"]) > 0 and dev["unresponsive"] == "False":
            result += 1
    return result


def ensure_checked_devices(central_node):
    json_model = json.loads(central_node.internalModel)
    start_time = time.time()
    checked_devs = checked_devices(json_model)
    while checked_devs != len(json_model["devices"]):
        new_checked_devs = checked_devices(json_model)
        if checked_devs != new_checked_devs:
            checked_devs = new_checked_devs
            logger.debug("checked devices: %s", checked_devs)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            logger.debug(central_node.internalModel)
            pytest.fail("Timeout occurred while executing the test")
        json_model = json.loads(central_node.internalModel)
    logger.debug("central_node.internalModel: %s", central_node.internalModel)


def assert_event_arrived():
    start_time = time.time()
    while not pytest.event_arrived:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.event_arrived

"""Conf test module for integration tests"""

# pylint: disable=redefined-outer-name
import json
import logging
import time

import pytest
from ska_tmc_common import (
    HelperBaseDevice,
    HelperCspMasterLeafDevice,
    HelperDishDevice,
    HelperDishLNDevice,
    HelperMCCSController,
    HelperMCCSMasterLeafNode,
    HelperSDPMasterLeafNode,
)
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_simulators.cn_helper_subarray_device import CNHelperSubArrayDevice
from tango.test_context import MultiDeviceTestContext

from ska_tmc_centralnode.central_node_low import LowTmcCentralNode
from ska_tmc_centralnode.central_node_mid import MidTmcCentralNode
from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
    DISH_DEVICE_PREFIX,
    DISH_LEAF_NODE_1,
    DISH_LEAF_NODE_PREFIX,
    DISH_MASTER_1,
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SUBARRAY_LN,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SUBARRAY_LN,
    LOW_TMC_SUBARRAY,
    MCCS_MASTER_DEVICE,
    MCCS_MLN_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SUBARRAY_LN,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SUBARRAY_LN,
    MID_TMC_SUBARRAY,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger

pytest.event_arrived = False


@pytest.fixture
def devices_to_load():
    """Devices to load for command invocations."""
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_TMC_SUBARRAY},
                {"name": LOW_TMC_SUBARRAY},
            ],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_CSP_SUBARRAY_LN},
                {"name": MID_SDP_SUBARRAY_LN},
                {"name": LOW_CSP_SUBARRAY_LN},
                {"name": LOW_SDP_SUBARRAY_LN},
            ],
        },
        {
            "class": HelperDishDevice,
            "devices": [
                {"name": DISH_MASTER_1},
            ],
        },
        {
            "class": HelperDishLNDevice,
            "devices": [
                {"name": DISH_LEAF_NODE_1},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
                {"name": LOW_CSP_MASTER_DEVICE},
                {"name": LOW_SDP_MASTER_DEVICE},
            ],
        },
        {
            "class": HelperMCCSMasterLeafNode,
            "devices": [
                {"name": MCCS_MLN_DEVICE},
            ],
        },
        {
            "class": HelperSDPMasterLeafNode,
            "devices": [
                {"name": MID_SDP_MLN_DEVICE},
                {"name": LOW_SDP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperCspMasterLeafDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": LOW_CSP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperMCCSController,
            "devices": [
                {"name": MCCS_MASTER_DEVICE},
            ],
        },
        {
            "class": MidTmcCentralNode,
            "devices": [
                {
                    "name": CENTRALNODE_MID,
                    "properties": {
                        "CspMasterLeafNodeFQDN": [MID_CSP_MLN_DEVICE],
                        "CspMasterFQDN": [MID_CSP_MASTER_DEVICE],
                        "SdpMasterLeafNodeFQDN": [MID_SDP_MLN_DEVICE],
                        "SdpMasterFQDN": [MID_SDP_MASTER_DEVICE],
                        "DishLeafNodePrefix": [DISH_LEAF_NODE_PREFIX],
                        "DishMasterIdentifier": [DISH_DEVICE_PREFIX],
                        "TMCMidSubarrayNodes": [MID_TMC_SUBARRAY],
                        "CspSubarrayLeafNodes": [MID_CSP_SUBARRAY_LN],
                        "SdpSubarrayLeafNodes": [MID_SDP_SUBARRAY_LN],
                        "DishIDs": ["SKA001"],
                    },
                }
            ],
        },
        {
            "class": LowTmcCentralNode,
            "devices": [
                {
                    "name": CENTRALNODE_LOW,
                    "properties": {
                        "CspMasterLeafNodeFQDN": [LOW_CSP_MLN_DEVICE],
                        "CspMasterFQDN": [LOW_CSP_MASTER_DEVICE],
                        "SdpMasterLeafNodeFQDN": [LOW_SDP_MLN_DEVICE],
                        "SdpMasterFQDN": [LOW_SDP_MASTER_DEVICE],
                        "MCCSMasterLeafNodeFQDN": [MCCS_MLN_DEVICE],
                        "MCCSMasterFQDN": [MCCS_MASTER_DEVICE],
                        "TMCLowSubarrayNodes": [LOW_TMC_SUBARRAY],
                        "CspSubarrayLeafNodes": [LOW_CSP_SUBARRAY_LN],
                        "SdpSubarrayLeafNodes": [LOW_SDP_SUBARRAY_LN],
                    },
                }
            ],
        },
    )


@pytest.fixture
def tango_context(devices_to_load, request):
    """Tango context method"""
    true_context = request.config.getoption("--true-context")
    logging.info("true context: %s", true_context)
    if not true_context:
        with MultiDeviceTestContext(devices_to_load, process=False) as context:
            DevFactory._test_context = context
            logging.info("test context set")
            yield context
    else:
        yield None


def checked_devices(json_model: dict) -> int:
    """Checked devices for availability"""
    result = 0
    for dev in json_model["devices"]:
        if dev["unresponsive"] == "False":
            result += 1
    return result


def ensure_checked_devices(central_node):
    """Ensures checked devices"""
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
    """Assert whether event arrived"""
    start_time = time.time()
    while not pytest.event_arrived:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.event_arrived

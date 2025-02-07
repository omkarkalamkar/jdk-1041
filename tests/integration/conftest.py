"""Conf test module for integration tests"""
# pylint: disable=redefined-outer-name
import json
import logging
import time

import pytest
from ska_tmc_common import (
    HelperBaseDevice,
    HelperDishDevice,
    HelperDishLNDevice,
    HelperMCCSController,
    HelperMCCSMasterLeafNode,
)
from ska_tmc_common.dev_factory import DevFactory
from tango.test_context import MultiDeviceTestContext

from ska_tmc_centralnode.central_node_low import LowTmcCentralNode
from ska_tmc_centralnode.central_node_mid import MidTmcCentralNode
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import SLEEP_TIME, TIMEOUT, logger

pytest.event_arrived = False


@pytest.fixture
def devices_to_load():
    """Devices to load for command invocations."""
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": "mid-tmc/subarray/01"},
                {"name": "low-tmc/subarray/01"},
            ],
        },
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": "mid-tmc/subarray-leaf-node-csp/01"},
                {"name": "mid-tmc/subarray-leaf-node-sdp/01"},
                {"name": "low-tmc/subarray-leaf-node-csp/01"},
                {"name": "low-tmc/subarray-leaf-node-sdp/01"},
            ],
        },
        {
            "class": HelperDishDevice,
            "devices": [
                {"name": "ska001/elt/master"},
            ],
        },
        {
            "class": HelperDishLNDevice,
            "devices": [
                {"name": "mid-tmc/leaf-node-dish/ska001"},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": "mid-tmc/leaf-node-csp/0"},
                {"name": "mid-csp/control/0"},
                {"name": "mid-tmc/leaf-node-sdp/0"},
                {"name": "mid-sdp/control/0"},
                {"name": "low-tmc/leaf-node-csp/0"},
                {"name": "low-csp/control/0"},
                {"name": "low-tmc/leaf-node-sdp/0"},
                {"name": "low-sdp/control/0"},
            ],
        },
        {
            "class": HelperMCCSMasterLeafNode,
            "devices": [
                {"name": "low-tmc/leaf-node-mccs/0"},
            ],
        },
        {
            "class": HelperMCCSController,
            "devices": [
                {"name": "low-mccs/control/control"},
            ],
        },
        {
            "class": MidTmcCentralNode,
            "devices": [
                {
                    "name": "mid-tmc/central-node/0",
                    "properties": {
                        "CspMasterLeafNodeFQDN": ["mid-tmc/leaf-node-csp/0"],
                        "CspMasterFQDN": ["mid-csp/control/0"],
                        "SdpMasterLeafNodeFQDN": ["mid-tmc/leaf-node-sdp/0"],
                        "SdpMasterFQDN": ["mid-sdp/control/0"],
                        "DishLeafNodePrefix": ["mid-tmc/leaf-node-dish/ska"],
                        "DishMasterIdentifier": ["elt/master"],
                        "TMCMidSubarrayNodes": ["mid-tmc/subarray/01"],
                        "CspSubarrayLeafNodes": [
                            "mid-tmc/subarray-leaf-node-csp/01"
                        ],
                        "SdpSubarrayLeafNodes": [
                            "mid-tmc/subarray-leaf-node-sdp/01"
                        ],
                        "DishIDs": ["SKA001"],
                    },
                }
            ],
        },
        {
            "class": LowTmcCentralNode,
            "devices": [
                {
                    "name": "low-tmc/central-node/0",
                    "properties": {
                        "CspMasterLeafNodeFQDN": ["low-tmc/leaf-node-csp/0"],
                        "CspMasterFQDN": ["low-csp/control/0"],
                        "SdpMasterLeafNodeFQDN": ["low-tmc/leaf-node-sdp/0"],
                        "SdpMasterFQDN": ["low-sdp/control/0"],
                        "MCCSMasterLeafNodeFQDN": ["low-tmc/leaf-node-mccs/0"],
                        "MCCSMasterFQDN": ["low-mccs/control/control"],
                        "TMCLowSubarrayNodes": ["low-tmc/subarray/01"],
                        "CspSubarrayLeafNodes": [
                            "low-tmc/subarray-leaf-node-csp/01"
                        ],
                        "SdpSubarrayLeafNodes": [
                            "low-tmc/subarray-leaf-node-sdp/01"
                        ],
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

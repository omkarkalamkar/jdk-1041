import json
import time
from logging import debug
from os.path import dirname, join

import pytest
import tango
from ska_tango_base.commands import ResultCode
from tango import DevState

from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.integration.test_on_command import checked_devices
from tests.settings import SLEEP_TIME, TIMEOUT, logger

devices_to_test = [
    {
        "class": HelperSubArrayDevice,
        "devices": [
            {"name": "ska_mid/tm_subarray_node/1"},
            {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
            {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
        ],
    },
    {
        "class": HelperStateDevice,
        "devices": [
            {"name": "ska_mid/tm_leaf_node/csp_master"},
            {"name": "mid_csp/elt/master"},
            {"name": "ska_mid/tm_leaf_node/sdp_master"},
            {"name": "mid_sdp/elt/master"},
            {"name": "mid_d0001/elt/master"},
            {"name": "ska_mid/tm_leaf_node/d0001"},
        ],
    },
    {
        "class": CentralNode,
        "devices": [
            {
                "name": "ska_mid/tm_central/central_node",
                "properties": {
                    "CspMasterLeafNodeFQDN": [
                        "ska_mid/tm_leaf_node/csp_master"
                    ],
                    "CspMasterFQDN": ["mid_csp/elt/master"],
                    "SdpMasterLeafNodeFQDN": [
                        "ska_mid/tm_leaf_node/sdp_master"
                    ],
                    "SdpMasterFQDN": ["mid_sdp/elt/master"],
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
]


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    path = join(dirname(__file__), "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def get_release_input_str(release_input_file="command_ReleaseResources.json"):
    path = join(dirname(__file__), "..", "data", release_input_file)
    with open(path, "r") as f:
        release_input_str = f.read()
    return release_input_str


@pytest.mark.post_deployment
def test_release_res_command(multi_device_tango_context):
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    logger.info("%s", multi_device_tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "InternalModel",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    json_model = json.loads(central_node.InternalModel)
    logger.info("json_model: %s", json_model["devices"])
    start_time = time.time()
    while checked_devices(json_model) != 9:
        logger.debug("checked devices: %s", checked_devices(json_model))
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        json_model = json.loads(central_node.InternalModel)
    initial_len = len(central_node.CommandExecuted)
    # (result, unique_id) = central_node.Off()
    (result, unique_id) = central_node.On()
    assign_input_str = get_assign_input_str()
    (result, unique_id) = central_node.AssignResources(assign_input_str)
    logger.info("command executed: %s", central_node.CommandExecuted)
    release_input_str = get_release_input_str()
    (result, unique_id) = central_node.ReleaseResources(release_input_str)
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.CommandExecuted) != initial_len + 3:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > 100:
            pytest.fail("Timeout occurred while executing the test")

    logger.info("command executed: %s", central_node.CommandExecuted)

    for command in central_node.CommandExecuted:
        if command[0] == unique_id[0]:
            logger.info("command result: %s", command)
            assert command[2] == "ResultCode.OK"

    start_time = time.time()
    while pytest.num_events_arrived <= 3:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived > 1

    json_model = json.loads(central_node.InternalModel)
    for device in json_model["devices"]:
        if device["dev_name"] == "ska_mid/tm_subarray_node/1":
            assert len(device["resources"]) == 0
            break

    (result, unique_id) = central_node.Off()

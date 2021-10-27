import json
import time
from os.path import dirname, join

import pytest
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    path = join(dirname(__file__), "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_assign_res_command(tango_context):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    ensure_checked_devices(central_node)
    initial_len = len(central_node.CommandExecuted)
    (result, unique_id) = central_node.On()
    assign_input_str = get_assign_input_str()
    (result, unique_id) = central_node.AssignResources(assign_input_str)
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.CommandExecuted) != initial_len + 2:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.CommandExecuted:
        if command[0] == unique_id[0]:
            logger.info("command result: %s", command)
            assert command[2] == "ResultCode.OK"

    def get_device(json_model):
        for device in json_model["devices"]:
            if device["dev_name"] == "ska_mid/tm_subarray_node/1":
                return device
        return None

    device = get_device(json.loads(central_node.InternalModel))
    start_time = time.time()
    while len(device["resources"]) == 0:
        time.sleep(SLEEP_TIME)
        device = get_device(json.loads(central_node.InternalModel))
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert len(device["resources"]) > 0

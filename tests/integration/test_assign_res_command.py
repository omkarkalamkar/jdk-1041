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
from tests.integration.device_to_load import devices_to_load
from tests.integration.test_on_command import checked_devices
from tests.settings import SLEEP_TIME, TIMEOUT, logger


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    path = join(dirname(__file__), "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


@pytest.mark.post_deployment
def test_assign_res_command(tango_context):
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "InternalModel",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    json_model = json.loads(central_node.InternalModel)
    start_time = time.time()
    checked_devs = checked_devices(json_model)
    while checked_devs != 9:
        new_checked_devs = checked_devices(json_model)
        if checked_devs != new_checked_devs:
            checked_devs = new_checked_devs
            logger.debug("checked devices: %s", checked_devs)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        json_model = json.loads(central_node.InternalModel)
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

    start_time = time.time()
    while pytest.num_events_arrived <= 2:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived > 1

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

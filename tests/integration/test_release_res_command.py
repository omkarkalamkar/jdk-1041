import json
import time
from os.path import dirname, join

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


def get_input_str(path):
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def get_mccs_device_resources(json_model):
    for device in json_model["devices"]:
        if device["dev_name"] == "ska_low/tm_leaf_node/mccs_master":
            mccs_device = device
    len_subarray_beam_ids = 0
    if "subarray_beam_ids" in mccs_device["resources"]:
        len_subarray_beam_ids = len(
            mccs_device["resources"]["subarray_beam_ids"]
        )
    len_station_ids = 0
    if "station_ids" in mccs_device["resources"]:
        len_subarray_beam_ids = len(mccs_device["resources"]["station_ids"])
    len_channel_blocks = 0
    if "channel_blocks" in mccs_device["resources"]:
        len_subarray_beam_ids = len(mccs_device["resources"]["channel_blocks"])
    return len_subarray_beam_ids + len_station_ids + len_channel_blocks


def release_resources(
    tango_context, central_node_name, assign_input_str, release_input_str
):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    ensure_checked_devices(central_node)
    initial_len = len(central_node.commandExecuted)
    # (result, unique_id) = central_node.Off()
    (result, unique_id) = central_node.On()
    (result, unique_id) = central_node.AssignResources(assign_input_str)
    (result, unique_id) = central_node.ReleaseResources(release_input_str)
    if result[0] != ResultCode.QUEUED:
        logger.error("Result: %s message: %s", result[0], unique_id)
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.commandExecuted) != initial_len + 3:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > 100:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.commandExecuted:
        if command[0] == unique_id[0]:
            logger.info("command result: %s", command)
            assert command[2] == "ResultCode.OK"

    def get_subarray_device(json_model):
        for device in json_model["devices"]:
            if device["dev_name"] == "ska_mid/tm_subarray_node/1":
                return device
        return None

    if "ska_mid" in central_node_name:
        device = get_subarray_device(json.loads(central_node.internalModel))
        start_time = time.time()
        while len(device["resources"]) != 0:
            time.sleep(SLEEP_TIME)
            device = get_subarray_device(
                json.loads(central_node.internalModel)
            )
            elapsed_time = time.time() - start_time
            if elapsed_time > TIMEOUT:
                pytest.fail("Timeout occurred while executing the test")

        assert len(device["resources"]) == 0

    if "ska_low" in central_node_name:
        resources_len = get_mccs_device_resources(
            json.loads(central_node.internalModel)
        )
        start_time = time.time()
        while resources_len != 0:
            time.sleep(SLEEP_TIME)
            resources_len = get_mccs_device_resources(
                json.loads(central_node.internalModel)
            )
            elapsed_time = time.time() - start_time
            if elapsed_time > TIMEOUT:
                pytest.fail("Timeout occurred while executing the test")

        assert resources_len == 0

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_release_res_command_mid(tango_context):
    return release_resources(
        tango_context,
        "ska_mid/tm_central/central_node",
        get_input_str(
            join(
                dirname(__file__), "..", "data", "command_AssignResources.json"
            )
        ),
        get_input_str(
            join(
                dirname(__file__),
                "..",
                "data",
                "command_ReleaseResources.json",
            )
        ),
    )

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_release_res_command_low(tango_context):
    return release_resources(
        tango_context,
        "ska_low/tm_central/central_node",
        get_input_str(
            join(
                dirname(__file__),
                "..",
                "data",
                "command_mccs_AssignResources.json",
            )
        ),
        get_input_str(
            join(
                dirname(__file__),
                "..",
                "data",
                "command_mccs_ReleaseResources.json",
            )
        ),
    )

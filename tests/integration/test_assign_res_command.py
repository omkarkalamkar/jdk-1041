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


def get_assign_input_str(path):
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def assign_resouces(tango_context, central_node_name, assign_input_str):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    ensure_checked_devices(central_node)
    initial_len = len(central_node.CommandExecuted)
    (result, unique_id) = central_node.On()
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

    def get_subarray_device(json_model):
        for device in json_model["devices"]:
            if device["dev_name"] == "ska_mid/tm_subarray_node/1":
                return device
        return None

    # def get_mccs_device(json_model):
    #     for device in json_model["devices"]:
    #         if device["dev_name"] == "low-mccs/control/control":
    #             return device
    #     return None

    def get_mccs_device_resources(json_model):
        resources_len = 0
        for device in json_model["devices"]:
            if device["dev_name"] == "low-mccs/control/control":
                mccs_device = device
        assigned_res_json = json.loads(mccs_device["resources"])
        resources_len = len(assigned_res_json["subarray_beam_ids"]) + len(assigned_res_json["station_ids"]) + len(
            assigned_res_json["channel_blocks"])
        
        return resources_len


    if "ska_mid" in central_node_name:
        device = get_subarray_device(json.loads(central_node.InternalModel))
        start_time = time.time()
        while len(device["resources"]) == 0:
            time.sleep(SLEEP_TIME)
            device = get_subarray_device(json.loads(central_node.InternalModel))
            elapsed_time = time.time() - start_time
            if elapsed_time > TIMEOUT:
                pytest.fail("Timeout occurred while executing the test")

        assert len(device["resources"]) > 0

    if "ska_low" in central_node_name:
        resources_len = get_mccs_device_resources(json.loads(central_node.InternalModel))
        start_time = time.time()
        while resources_len == 0:
            time.sleep(SLEEP_TIME)
            resources_len = get_mccs_device_resources(json.loads(central_node.InternalModel))
            elapsed_time = time.time() - start_time
            if elapsed_time > TIMEOUT:
                pytest.fail("Timeout occurred while executing the test")
        assert resources_len > 0

@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_assign_res_command_mid(tango_context, central_node_name):
    return assign_resouces(
        tango_context,
        central_node_name,
        get_assign_input_str(
            join(
                dirname(__file__), "..", "data", "command_AssignResources.json"
            )
        ),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_low/tm_central/central_node")],
)
def test_assign_res_command_low(tango_context, central_node_name):
    return assign_resouces(
        tango_context,
        central_node_name,
        get_assign_input_str(
            join(
                dirname(__file__),
                "..",
                "data",
                "low",
                "command_AssignResources.json",
            )
        ),
    )

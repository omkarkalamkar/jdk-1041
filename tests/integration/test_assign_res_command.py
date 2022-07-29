import json
import time
from os.path import dirname, join

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


def get_assign_input_str(path):
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def assign_resouces(
    tango_context, central_node_name, assign_input_str, change_event_callbacks
):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    result, unique_id = central_node.AssignResources(assign_input_str)

    logger.info(f"result is:{result}")
    logger.info(f"unique_id is:{unique_id}")

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED
    logger.info("Asserted resultcode as queued")
    central_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandsInQueue"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandsInQueue",
        (
            "TelescopeOn",
            "AssignResources",
        ),
    )

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )

    def get_subarray_device(json_model):
        for device in json_model["devices"]:
            if device["dev_name"] == "ska_mid/tm_subarray_node/1":
                return device
        return None

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
            len_subarray_beam_ids = len(
                mccs_device["resources"]["station_ids"]
            )
        len_channel_blocks = 0
        if "channel_blocks" in mccs_device["resources"]:
            len_subarray_beam_ids = len(
                mccs_device["resources"]["channel_blocks"]
            )
        return len_subarray_beam_ids + len_station_ids + len_channel_blocks

    if "ska_mid" in central_node_name:
        device = get_subarray_device(json.loads(central_node.internalModel))
        start_time = time.time()
        while len(device["resources"]) == 0:
            time.sleep(SLEEP_TIME)
            device = get_subarray_device(
                json.loads(central_node.internalModel)
            )
            elapsed_time = time.time() - start_time
            if elapsed_time > TIMEOUT:
                pytest.fail("Timeout occurred while executing the test")

        assert len(device["resources"]) > 0

    if "ska_low" in central_node_name:
        resources_len = get_mccs_device_resources(
            json.loads(central_node.internalModel)
        )
        start_time = time.time()
        while resources_len == 0:
            time.sleep(SLEEP_TIME)
            resources_len = get_mccs_device_resources(
                json.loads(central_node.internalModel)
            )
            elapsed_time = time.time() - start_time
            if elapsed_time > TIMEOUT:
                pytest.fail("Timeout occurred while executing the test")
        assert resources_len > 0


@pytest.mark.lily
# @pytest.mark.xfail(
#     reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
# )
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_assign_res_command_mid(
    tango_context, central_node_name, change_event_callbacks
):
    return assign_resouces(
        tango_context,
        central_node_name,
        get_assign_input_str(
            join(
                dirname(__file__), "..", "data", "command_AssignResources.json"
            )
        ),
        change_event_callbacks,
    )


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_low/tm_central/central_node")],
)
def test_assign_res_command_low(
    tango_context, central_node_name, change_event_callbacks
):
    return assign_resouces(
        tango_context,
        central_node_name,
        get_assign_input_str(
            join(
                dirname(__file__),
                "..",
                "data",
                "command_mccs_AssignResources.json",
            )
        ),
        change_event_callbacks,
    )

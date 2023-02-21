import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_cdm.exceptions import JsonValidationError
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    LOW_SUBARRAY_DEVICE,
    MID_SUBARRAY_DEVICE,
    SLEEP_TIME,
    TIMEOUT,
    logger,
)


def assign_resources(
    tango_context,
    central_node_name,
    assign_input_str,
    change_event_callbacks,
    subarray_device,
):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    if "ska_mid" in central_node_name:
        result, unique_id = central_node.AssignResources(
            json.dumps(assign_input_str)
        )
    else:
        result, unique_id = central_node.AssignResources(assign_input_str)
    logger.info(
        f"AssignResources Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

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
            if device["dev_name"] == subarray_device:
                return device
        return None

    # TODO Uncomment below code during integration of MCCS
    # def get_mccs_device_resources(json_model):
    #     for device in json_model["devices"]:
    #         if device["dev_name"] == "ska_low/tm_leaf_node/mccs_master":
    #             return device
    #     len_subarray_beam_ids = 0
    #     if "subarray_beam_ids" in mccs_device["resources"]:
    #         len_subarray_beam_ids = len(
    #             mccs_device["resources"]["subarray_beam_ids"]
    #         )
    #     len_station_ids = 0
    #     if "station_ids" in mccs_device["resources"]:
    #         len_subarray_beam_ids = len(
    #             mccs_device["resources"]["station_ids"]
    #         )
    #     len_channel_blocks = 0
    #     if "channel_blocks" in mccs_device["resources"]:
    #         len_subarray_beam_ids = len(
    #             mccs_device["resources"]["channel_blocks"]
    #         )
    #     return len_subarray_beam_ids + len_station_ids + len_channel_blocks

    device = get_subarray_device(json.loads(central_node.internalModel))
    logger.debug(f"InternalModel attribute value is:{device}")
    start_time = time.time()
    while len(device["resources"]) == 0:
        time.sleep(SLEEP_TIME)
        device = get_subarray_device(json.loads(central_node.internalModel))
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert len(device["resources"]) > 0

    # TODO Uncomment below code during integration of MCCS
    # if "ska_low" in central_node_name:
    #     device = get_mccs_device_resources(
    #         json.loads(central_node.internalModel)
    #     )
    #     start_time = time.time()
    #     while len(device["resources"]) == 0:
    #         time.sleep(SLEEP_TIME)
    #         device = get_mccs_device_resources(
    #             json.loads(central_node.internalModel)
    #         )
    #         elapsed_time = time.time() - start_time
    #         if elapsed_time > TIMEOUT:
    #             pytest.fail("Timeout occurred while executing the test")
    # while resources_len == 0:
    #     time.sleep(SLEEP_TIME)
    #     resources_len = get_mccs_device_resources(
    #         json.loads(central_node.internalModel)
    #     )
    #     elapsed_time = time.time() - start_time
    #     if elapsed_time > TIMEOUT:
    #         pytest.fail("Timeout occurred while executing the test")
    # assert len(device["resources"]) > 0

    # teardown subarray, setting ObsState = Empty
    tmc_subarray = dev_factory.get_device(subarray_device)
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_assign_res_command_mid(
    tango_context, central_node_name, change_event_callbacks, json_factory
):
    return assign_resources(
        tango_context,
        central_node_name,
        json_factory("command_AssignResources"),
        change_event_callbacks,
        MID_SUBARRAY_DEVICE,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_low/tm_central/central_node")],
)
def test_assign_res_command_low(
    tango_context, central_node_name, change_event_callbacks, json_factory
):
    return assign_resources(
        tango_context,
        central_node_name,
        json_factory("command_assign_resource_low"),
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
    )


def assign_resources_with_invalid_json(
    tango_context,
    central_node_name,
    assign_input_str,
    change_event_callbacks,
    subarray_device,
):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    if "ska_mid" in central_node_name:
        with pytest.raises(ValueError, JsonValidationError("Error")):
            result, message = central_node.AssignResources(
                json.dumps(assign_input_str)
            )
    else:
        result, message = central_node.AssignResources(assign_input_str)
        assert [
            "subarray_id key is not present in the input json argument."
        ] == message

    logger.info(f"Message::{message}")
    assert result[0] == ResultCode.REJECTED


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_assign_res_command_mid_invalid_json(
    tango_context, central_node_name, change_event_callbacks, json_factory
):
    return assign_resources_with_invalid_json(
        tango_context,
        central_node_name,
        json_factory("invalid_key_AssignResources"),
        change_event_callbacks,
        MID_SUBARRAY_DEVICE,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_low/tm_central/central_node")],
)
def test_assign_res_command_low_invalid_json(
    tango_context, central_node_name, change_event_callbacks, json_factory
):
    return assign_resources_with_invalid_json(
        tango_context,
        central_node_name,
        json_factory("invalid_key_AssignResources"),
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
    )

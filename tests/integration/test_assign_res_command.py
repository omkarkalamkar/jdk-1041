"""Test module for AssignResources command."""
import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
)
from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    ERROR_PROPAGATION_DEFECT,
    LOW_CENTRAL_NODE,
    LOW_SUBARRAY_DEVICE,
    MID_SUBARRAY_DEVICE,
    RESET_DEFECT,
    SLEEP_TIME,
    TIMEOUT,
    TIMEOUT_DEFECT,
    check_subarray_availability,
    logger,
)


def assign_resources(
    tango_context,
    central_node_name,
    assign_input_str,
    release_input_string,
    change_event_callbacks,
    subarray_device,
):
    """AssignResources Test method."""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    subarray_proxy = dev_factory.get_device(subarray_device)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "Telscope On Command ID: %s Returned result: %s",
        unique_id,
        result,
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
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, subarray_device, True)

    if "mid-tmc" in central_node_name:
        result, unique_id = central_node.AssignResources(assign_input_str)
    else:
        result, unique_id = central_node.AssignResources(assign_input_str)
    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    def get_subarray_device(json_model):
        for device in json_model["devices"]:
            if device["dev_name"] == subarray_device:
                return device
        return None

    # TODO Uncomment below code during integration of MCCS
    # def get_mccs_device_resources(json_model):
    #     for device in json_model["devices"]:
    #         if device["dev_name"] == "low-tmc/leaf-node-mccs/0":
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
    logger.debug("InternalModel attribute value is:%s", device)
    start_time = time.time()
    while len(device["resources"]) == 0:
        time.sleep(SLEEP_TIME)
        device = get_subarray_device(json.loads(central_node.internalModel))
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert len(device["resources"]) > 0

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    result, unique_id = central_node.ReleaseResources(release_input_string)
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

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

    result, unique_id = central_node.TelescopeOff()


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [(CENTRALNODE_MID)],
)
def test_assign_res_command_mid(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test assign Resources command for mid"""
    return assign_resources(
        tango_context,
        central_node_name,
        json_factory("command_AssignResources"),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
        MID_SUBARRAY_DEVICE,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [(CENTRALNODE_LOW)],
)
def test_assign_res_command_low(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
):
    """Test assign Resources command for low"""
    return assign_resources(
        tango_context,
        central_node_name,
        json_factory("command_assign_resource_low"),
        json_factory("command_release_resource_low"),
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
    """Test assign resources with invalid json."""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    subarray_proxy = dev_factory.get_device(subarray_device)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "TelescopeOn Command ID: %s Returned result: %s",
        unique_id,
        result,
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
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, subarray_device, True)

    result, message = central_node.AssignResources(assign_input_str)

    assert (
        "subarray_id key is not present in the input json argument"
        in message[0]
    )
    assert result[0] == ResultCode.REJECTED

    # Teardown
    result, unique_id = central_node.TelescopeOff()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [(CENTRALNODE_LOW)],
)
def test_assign_res_command_low_invalid_json(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
):
    """Test assign resources for low invalid json"""
    return assign_resources_with_invalid_json(
        tango_context,
        central_node_name,
        json_factory("invalid_key_AssignResources"),
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
    )


def assign_resources_without_subarray_id(
    tango_context,
    central_node_name,
    assign_input_str,
    change_event_callbacks,
):
    """Test Assign Resources without subarray id"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "TelescopeOn Command ID: %s Returned result: %s", unique_id, result
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
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, message = central_node.AssignResources(assign_input_str)

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert (
        "subarray_id key is not present in the input json argument"
        in message[0]
    )
    assert result[0] == ResultCode.REJECTED

    result, unique_id = central_node.TelescopeOff()
    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("TelescopeOff")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [(CENTRALNODE_MID)],
)
def test_assign_res_command_mid_without_subarray_id(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test assign Resources command mid without subarray id"""
    return assign_resources_without_subarray_id(
        tango_context,
        central_node_name,
        json_factory("invalid_key_AssignResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_assign_resources_exception_propagation(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test Assign Resources exception propagation"""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
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
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    tmc_subarray = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    tmc_subarray.SetDefective(ERROR_PROPAGATION_DEFECT)

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.AssignResources(
        json_factory("command_AssignResources")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    event_data = change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], Anything),
        lookahead=8,
    )
    exception_message = (
        f"{MID_SUBARRAY_DEVICE}: Exception occurred, command failed."
    )
    assert exception_message in event_data["attribute_value"][1]

    tmc_subarray.SetDefective(RESET_DEFECT)
    # Teardown
    result, unique_id = central_node.TelescopeOff()
    tmc_subarray.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_assign_resources_mid_timeout(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test Assign Resources mid timeout"""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
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
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    tmc_subarray = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    tmc_subarray.SetDefective(TIMEOUT_DEFECT)

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.AssignResources(
        json_factory("command_AssignResources")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id[0],
            json.dumps(
                (
                    int(ResultCode.FAILED),
                    "Timeout has occurred, command failed",
                )
            ),
        ),
        lookahead=4,
    )
    tmc_subarray.SetDefective(RESET_DEFECT)
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)

    # Teardown
    result, unique_id = central_node.TelescopeOff()
    tmc_subarray.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_assign_resources_low_timeout(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
):
    """Test Assign Resources low timeout"""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(LOW_CENTRAL_NODE)
    subarray_proxy = dev_factory.get_device(LOW_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "Telescope On Command ID: %s Returned result: %s", unique_id, result
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
        (
            unique_id[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=4,
    )

    tmc_subarray = DevFactory().get_device(LOW_SUBARRAY_DEVICE)
    tmc_subarray.SetDefective(TIMEOUT_DEFECT)

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.AssignResources(
        json_factory("command_assign_resource_low")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id[0],
            json.dumps(
                (
                    int(ResultCode.FAILED),
                    "Timeout has occurred, command failed",
                )
            ),
        ),
        lookahead=4,
    )
    tmc_subarray.SetDefective(RESET_DEFECT)
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)

    # Teardown
    result, unique_id = central_node.TelescopeOff()
    tmc_subarray.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_assign_resources_low_error_aggregation(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
):
    """Test Assign Resources low error aggregation"""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(LOW_CENTRAL_NODE)
    subarray_proxy = dev_factory.get_device(LOW_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "TelescopeOn Command ID: %s Returned result: %s", unique_id, result
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
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    subarray_proxy.SetDefective(ERROR_PROPAGATION_DEFECT)

    result, unique_id = central_node.AssignResources(
        json_factory("command_assign_resource_low")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    event_data = change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], Anything),
        lookahead=8,
    )
    exception_message = (
        f"{LOW_SUBARRAY_DEVICE}:" + " Exception occurred, command failed."
    )

    assert exception_message in event_data["attribute_value"][1]
    subarray_proxy.SetDefective(RESET_DEFECT)

    # Teardown
    result, unique_id = central_node.TelescopeOff()
    subarray_proxy.ClearCommandCallInfo()

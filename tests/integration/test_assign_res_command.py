"""Test module for AssignResources command."""

import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_testing.mock.placeholders import Anything

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
)
from tests.integration.conftest import get_cn_sn
from tests.settings import (
    ERROR_PROPAGATION_DEFECT,
    LOW_SUBARRAY_DEVICE,
    MID_SUBARRAY_DEVICE,
    SLEEP_TIME,
    TIMEOUT,
    TIMEOUT_DEFECT,
    TIMEOUT_MSG,
    assert_exception,
    clean_up_subarray,
    logger,
    set_auto_recovery_for_low,
    telescope_off,
    telescope_on,
)


def assign_resources(
    central_node_name,
    assign_input_str,
    release_input_string,
    change_event_callbacks,
    subarray_device,
):
    """AssignResources Test method."""
    central_node, subarray_proxy, _ = get_cn_sn(central_node_name)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)
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

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    result, unique_id = central_node.ReleaseResources(release_input_string)
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    subarray_proxy.SetDirectObsState(ObsState.EMPTY)

    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name, input_json",
    [
        (CENTRALNODE_MID, "command_AssignResources_with_mkt"),
        (CENTRALNODE_MID, "command_AssignResources"),
        (CENTRALNODE_MID, "command_AssignResources_2_1"),
    ],
)
@pytest.mark.usefixtures(
    "set_mid_sdp_csp_mln_availability_for_aggregation",
    "set_mid_sdp_csp_admin_modes",
)
def test_assign_res_command_mid(
    central_node_name,
    input_json,
    change_event_callbacks,
    json_factory,
):
    """Test assign Resources command for mid"""
    return assign_resources(
        central_node_name,
        json_factory(input_json),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
        MID_SUBARRAY_DEVICE,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name, input_json",
    [
        (CENTRALNODE_LOW, "assign_resource_low"),
        (CENTRALNODE_LOW, "assign_resource_low_4_0"),
        (CENTRALNODE_LOW, "assign_resource_low_without_mccs_4_2"),
        (CENTRALNODE_LOW, "assign_resource_low_without_csp_4_2"),
        (CENTRALNODE_LOW, "assign_resource_low_without_sdp_4_2"),
    ],
)
@pytest.mark.usefixtures(
    "set_low_devices_availability_for_aggregation",
    "set_low_sdp_csp_mccs_admin_modes",
)
def test_assign_res_command_low(
    central_node_name, input_json, change_event_callbacks, json_factory
):
    """Test assign Resources command for low"""
    return assign_resources(
        central_node_name,
        json_factory(input_json),
        json_factory("release_resource_low"),
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
    )


@pytest.mark.post_deployment
@pytest.mark.auto_recovery
def test_assign_res_command_low_with_auto_recovery(
    change_event_callbacks,
    json_factory,
):
    """Test assign Resources command for low"""
    set_auto_recovery_for_low(CENTRALNODE_LOW)
    return assign_resources(
        CENTRALNODE_LOW,
        json_factory("assign_resource_low"),
        json_factory("release_resource_low"),
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
    )


def assign_resources_with_invalid_json(
    central_node_name, assign_input_str, change_event_callbacks
):
    """Test assign resources with invalid json."""
    central_node, _, _ = get_cn_sn(central_node_name)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    result, message = central_node.AssignResources(assign_input_str)

    assert (
        "subarray_id key is not present in the input json argument"
        in message[0]
    )
    assert result[0] == ResultCode.REJECTED

    # Teardown
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_LOW],
)
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_assign_res_command_low_invalid_json(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test assign resources for low invalid json"""
    return assign_resources_with_invalid_json(
        central_node_name,
        json_factory("invalid_key_AssignResources"),
        change_event_callbacks,
    )


def assign_resources_without_subarray_id(
    central_node_name,
    assign_input_str,
    change_event_callbacks,
):
    """Test Assign Resources without subarray id"""
    central_node, _, _ = get_cn_sn(central_node_name)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    result, message = central_node.AssignResources(assign_input_str)

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        result,
        message,
    )

    assert (
        "subarray_id key is not present in the input json argument"
        in message[0]
    )
    assert result[0] == ResultCode.REJECTED

    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
@pytest.mark.usefixtures(
    "set_mid_sdp_csp_mln_availability_for_aggregation",
    "set_mid_sdp_csp_admin_modes",
)
def test_assign_res_command_mid_without_subarray_id(
    central_node_name, change_event_callbacks, json_factory
):
    """Test assign Resources command mid without subarray id"""
    return assign_resources_without_subarray_id(
        central_node_name,
        json_factory("invalid_key_AssignResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_assign_resources_exception_propagation(
    change_event_callbacks,
    json_factory,
):
    """Test Assign Resources exception propagation"""
    central_node, subarray_proxy, _ = get_cn_sn(CENTRALNODE_MID)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    telescope_on(central_node, change_event_callbacks)

    subarray_proxy.SetDefective(ERROR_PROPAGATION_DEFECT)

    result, unique_id = central_node.AssignResources(
        json_factory("command_AssignResources")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    event_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=8,
    )
    exception_message = (
        f"{MID_SUBARRAY_DEVICE}: Exception occurred, command failed."
    )
    assert exception_message in event_data["attribute_value"][1]

    # Teardown
    clean_up_subarray(subarray_proxy)
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_assign_resources_mid_timeout(
    change_event_callbacks,
    json_factory,
):
    """Test Assign Resources mid timeout"""

    central_node, subarray_proxy, _ = get_cn_sn(CENTRALNODE_MID)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    subarray_proxy.SetDefective(TIMEOUT_DEFECT)

    result, unique_id = central_node.AssignResources(
        json_factory("command_AssignResources")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    assert_exception(unique_id, TIMEOUT_MSG, change_event_callbacks)

    # Teardown
    clean_up_subarray(subarray_proxy)
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_assign_resources_low_timeout(change_event_callbacks, json_factory):
    """Test Assign Resources low timeout"""

    central_node, subarray_proxy, _ = get_cn_sn(CENTRALNODE_LOW)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    subarray_proxy.SetDefective(TIMEOUT_DEFECT)

    result, unique_id = central_node.AssignResources(
        json_factory("assign_resource_low")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    assert_exception(unique_id, TIMEOUT_MSG, change_event_callbacks)
    clean_up_subarray(subarray_proxy)
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_assign_resources_low_error_aggregation(
    change_event_callbacks, json_factory
):
    """Test Assign Resources low error aggregation"""

    central_node, subarray_proxy, _ = get_cn_sn(CENTRALNODE_LOW)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    subarray_proxy.SetDefective(ERROR_PROPAGATION_DEFECT)

    result, unique_id = central_node.AssignResources(
        json_factory("assign_resource_low")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED

    event_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=8,
    )
    exception_message = (
        f"{LOW_SUBARRAY_DEVICE}: Exception occurred, command failed."
    )

    assert exception_message in event_data["attribute_value"][1]

    # Teardown
    clean_up_subarray(subarray_proxy)
    telescope_off(central_node, change_event_callbacks)

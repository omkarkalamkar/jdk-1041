"""Test cases for rlease resources command"""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
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
    TIMEOUT_DEFECT,
    TIMEOUT_MSG,
    assert_exception,
    assign_resources,
    check_subarray_availability,
    clean_up_subarray,
    logger,
    set_auto_recovery_for_low,
    telescope_off,
    telescope_on,
)


def release_resources(
    central_node_name,
    assign_input_str,
    release_input_string,
    change_event_callbacks,
):
    """Method for rlease resources command"""
    central_node, _, _ = get_cn_sn(central_node_name)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    assign_resources(central_node, assign_input_str, change_event_callbacks)

    result, unique_id = central_node.ReleaseResources(release_input_string)

    logger.info("Unique id:%s", unique_id[0])
    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )
    # Teardown
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_release_resources_mid_timeout(
    change_event_callbacks,
    json_factory,
):
    """Test cases for release resources command for mid timeout."""
    central_node, subarray_proxy, _ = get_cn_sn(CENTRALNODE_MID)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    assign_resources(
        central_node,
        json_factory("command_AssignResources"),
        change_event_callbacks,
    )

    subarray_proxy.SetDefective(TIMEOUT_DEFECT)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_ReleaseResources")
    )

    logger.info(
        "ReleaseResources Command ID: %s Returned result: %s ",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    assert_exception(unique_id, TIMEOUT_MSG, change_event_callbacks)

    # Teardown
    clean_up_subarray(subarray_proxy)
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_release_res_command_mid(
    change_event_callbacks,
    json_factory,
):
    """Test cases for rlease resources command for low"""
    return release_resources(
        CENTRALNODE_MID,
        json_factory("command_AssignResources"),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_release_res_command_low(
    change_event_callbacks,
    json_factory,
):
    """Test cases for release resources command"""
    return release_resources(
        CENTRALNODE_LOW,
        json_factory("assign_resource_low"),
        json_factory("release_resource_low"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.auto_recovery
def test_release_res_command_low_with_auto_recovery(
    change_event_callbacks, json_factory
):
    """Test cases for release resources command"""
    set_auto_recovery_for_low(CENTRALNODE_LOW)
    return release_resources(
        CENTRALNODE_LOW,
        json_factory("assign_resource_low"),
        json_factory("release_resource_low"),
        change_event_callbacks,
    )


def release_resources_without_subarray_id(
    central_node_name,
    assign_input_str,
    invalid_release_input_string,
    release_input_string,
    change_event_callbacks,
):
    """Invokes release resources command without subarray id"""
    central_node, _, _ = get_cn_sn(central_node_name)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    result, unique_id_assign = central_node.AssignResources(assign_input_str)

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            unique_id_assign[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=4,
    )

    result, message = central_node.ReleaseResources(
        invalid_release_input_string
    )

    assert (
        "subarray_id key is not present in the input json argument"
        in message[0]
    )
    assert result[0] == ResultCode.REJECTED

    result, unique_id = central_node.ReleaseResources(release_input_string)

    logger.info("Unique id:%s", unique_id[0])
    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_release_res_command_mid_without_subarray_id(
    change_event_callbacks,
    json_factory,
):
    """Test cases for release resources command without subarray id"""
    return release_resources_without_subarray_id(
        CENTRALNODE_MID,
        json_factory("command_AssignResources"),
        json_factory("command_ReleaseResources_without_subarray_id"),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_release_resources_error_propagation(
    change_event_callbacks, json_factory
):
    """Test cases for release resources error propagation command."""
    central_node, subarray_proxy, _ = get_cn_sn(CENTRALNODE_MID)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

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

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )
    subarray_proxy.SetDefective(ERROR_PROPAGATION_DEFECT)

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_ReleaseResources")
    )

    logger.info(
        "ReleaseResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED
    event_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=8,
    )
    exception_message = (
        f"{MID_SUBARRAY_DEVICE}:" + " Exception occurred, command failed."
    )

    assert exception_message in event_data["attribute_value"][1]

    # Teardown
    clean_up_subarray(subarray_proxy)
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_release_resources_low_timeout(
    change_event_callbacks,
    json_factory,
):
    """Test cases for release resources command for low timeout."""
    central_node, subarray_proxy, _ = get_cn_sn(CENTRALNODE_LOW)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

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

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )

    subarray_proxy.SetDefective(TIMEOUT_DEFECT)
    check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.ReleaseResources(
        json_factory("release_resource_low")
    )

    logger.info(
        "ReleaseResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            unique_id[0],
            json.dumps(
                (
                    int(ResultCode.FAILED),
                    "Timeout has occurred, command failed",
                )
            ),
        ),
        lookahead=6,
    )

    # Teardown
    clean_up_subarray(subarray_proxy)
    telescope_off(central_node, change_event_callbacks)


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_release_resources_error_aggregation(
    change_event_callbacks,
    json_factory,
):
    """Test Release Resources error propagation."""
    central_node, subarray_proxy, _ = get_cn_sn(CENTRALNODE_LOW)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

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

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )

    subarray_proxy.SetDefective(ERROR_PROPAGATION_DEFECT)

    result, unique_id = central_node.ReleaseResources(
        json_factory("release_resource_low")
    )

    logger.info(
        "ReleaseResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    event_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=8,
    )
    exception_message = (
        f"{LOW_SUBARRAY_DEVICE}:" + " Exception occurred, command failed."
    )

    assert exception_message in event_data["attribute_value"][1]
    # Teardown
    clean_up_subarray(subarray_proxy)
    telescope_off(central_node, change_event_callbacks)

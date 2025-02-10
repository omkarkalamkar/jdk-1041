"""Test cases for rlease resources command"""
import json

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
    TIMEOUT_DEFECT,
    check_subarray_availability,
    event_remover,
    logger,
)


def release_resources(
    tango_context,
    central_node_name,
    assign_input_str,
    release_input_string,
    change_event_callbacks,
):
    """Method for rlease resources command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    if "mid-tmc" in central_node_name:
        subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    else:
        subarray_proxy = dev_factory.get_device(LOW_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id_on = central_node.TelescopeOn()
    assert unique_id_on[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            unique_id_on[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=6,
    )

    subarray_proxy.SetisSubarrayAvailable(True)
    if "mid-tmc" in central_node_name:
        check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)
    else:
        check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    if "mid-tmc" in central_node_name:
        result, unique_id_assign = central_node.AssignResources(
            assign_input_str
        )
    else:
        result, unique_id_assign = central_node.AssignResources(
            assign_input_str
        )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id_assign[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=6,
    )

    result, unique_id = central_node.ReleaseResources(release_input_string)

    logger.info("Unique id:%s", unique_id[0])
    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )

    # Teardown
    result, unique_id = central_node.TelescopeOff()


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_release_res_command_mid(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test cases for rlease resources command for low"""
    return release_resources(
        tango_context,
        CENTRALNODE_MID,
        json_factory("command_AssignResources"),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_release_res_command_low(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
):
    """Test cases for release resources command"""
    return release_resources(
        tango_context,
        CENTRALNODE_LOW,
        json_factory("command_assign_resource_low"),
        json_factory("command_release_resource_low"),
        change_event_callbacks,
    )


def release_resources_without_subarray_id(
    tango_context,
    central_node_name,
    assign_input_str,
    invalid_release_input_string,
    release_input_string,
    change_event_callbacks,
):
    """Invokes release resources command without subarray id"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    ensure_checked_devices(central_node)

    result, unique_id_on = central_node.TelescopeOn()
    assert unique_id_on[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            unique_id_on[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=4,
    )

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id_assign = central_node.AssignResources(assign_input_str)

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
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

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    result, unique_id = central_node.TelescopeOff()
    logger.info(
        "Telscope Off Command ID: %s Returned result: %s",
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
    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult"],
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_release_res_command_mid_without_subarray_id(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test cases for release resources command without subarray id"""
    return release_resources_without_subarray_id(
        tango_context,
        CENTRALNODE_MID,
        json_factory("command_AssignResources"),
        json_factory("command_ReleaseResources_without_subarray_id"),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_release_resources_error_propagation(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test cases for release resources error propagation command."""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "TelescopeID Command ID: %s Returned result: %s",
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
        lookahead=5,
    )

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

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )
    tmc_subarray = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    tmc_subarray.SetDefective(ERROR_PROPAGATION_DEFECT)

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_ReleaseResources")
    )

    logger.info(
        "ReleaseResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED
    event_data = change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], Anything),
        lookahead=8,
    )
    exception_message = (
        f"{MID_SUBARRAY_DEVICE}:" + " Exception occurred, command failed."
    )

    assert exception_message in event_data["attribute_value"][1]
    tmc_subarray.SetDefective(RESET_DEFECT)
    # Tear Down
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)
    # Teardown
    result, unique_id = central_node.TelescopeOff()
    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult"],
    )
    tmc_subarray.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_release_resources_mid_timeout(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test cases for release resources command for mid timeout."""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)
    subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_proxy.SetisSubarrayAvailable(True)
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
        lookahead=5,
    )

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

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )

    tmc_subarray = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    tmc_subarray.SetDefective(TIMEOUT_DEFECT)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_ReleaseResources")
    )

    logger.info(
        "ReleaseResources Command ID: %s Returned result: %s ",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("ReleaseResources")
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
        lookahead=8,
    )
    tmc_subarray.SetDefective(RESET_DEFECT)
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)
    # Teardown
    result, unique_id = central_node.TelescopeOff()
    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult"],
    )
    tmc_subarray.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_release_resources_low_timeout(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
):
    """Test cases for release resources command for low timeout."""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(LOW_CENTRAL_NODE)
    subarray_proxy = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_proxy.SetisSubarrayAvailable(True)
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

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )

    tmc_subarray = DevFactory().get_device(LOW_SUBARRAY_DEVICE)
    tmc_subarray.SetDefective(TIMEOUT_DEFECT)
    check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_release_resource_low")
    )

    logger.info(
        "ReleaseResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("ReleaseResources")
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
        lookahead=6,
    )
    tmc_subarray.SetDefective(RESET_DEFECT)
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)
    # Teardown
    result, unique_id = central_node.TelescopeOff()

    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult"],
    )
    tmc_subarray.ClearCommandCallInfo()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_release_resources_error_aggregation(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
):
    """Test Release Resources error propagation."""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(LOW_CENTRAL_NODE)
    subarray_proxy = dev_factory.get_device(LOW_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "TelescopeOn Command ID: %s  Returned result: %s",
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
        lookahead=5,
    )
    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.AssignResources(
        json_factory("command_assign_resource_low")
    )

    logger.info(
        "AssignResources Command ID: %s Returned result: %s", unique_id, result
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
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=6,
    )

    subarray_proxy.SetDefective(ERROR_PROPAGATION_DEFECT)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_release_resource_low")
    )

    logger.info(
        "ReleaseResources Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("ReleaseResources")
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
    subarray_proxy.ReleaseAllResources()
    subarray_proxy.SetDirectObsState(ObsState.EMPTY)
    result, unique_id = central_node.TelescopeOff()
    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult"],
    )
    subarray_proxy.ClearCommandCallInfo()

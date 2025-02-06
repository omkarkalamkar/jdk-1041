"""Test cases for release resources command"""
import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    LOW_SUBARRAY_DEVICE,
    MID_SUBARRAY_DEVICE,
    check_subarray_availability,
    logger,
)


def release_resources(
    tango_context,
    central_node_fqdn,
    assign_input_str,
    release_input_string,
    change_event_callbacks,
):
    """Release Resources method for command invocation."""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_fqdn)
    if "ska_mid" in central_node_fqdn:
        subarray_fqdn = MID_SUBARRAY_DEVICE
        subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    else:
        subarray_fqdn = LOW_SUBARRAY_DEVICE
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
        lookahead=4,
    )

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, subarray_fqdn, True)

    if "ska_mid" in central_node_fqdn:
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
        lookahead=4,
    )

    subarray_proxy.SetisSubarrayAvailable(False)
    check_subarray_availability(central_node, subarray_fqdn, False)

    result, unique_id = central_node.ReleaseResources(release_input_string)

    assert result[0] == ResultCode.REJECTED

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, subarray_fqdn, True)

    result, unique_id = central_node.ReleaseResources(release_input_string)

    logger.info("Unique id:%s", unique_id[0])
    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    result_off, unique_id_off = central_node.TelescopeOff()
    assert result_off[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id_off[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=4,
    )


@pytest.mark.skip(
    reason="This functionality is not present in the current version"
)
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_release_res_command_mid(
    tango_context, change_event_callbacks, json_factory
):
    """Test release resources command mid"""
    return release_resources(
        tango_context,
        "mid-tmc/central-node/0",
        json_factory("command_AssignResources"),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_release_res_command_low(
    tango_context, change_event_callbacks, json_factory
):
    """Test release resources command for low"""
    return release_resources(
        tango_context,
        "low-tmc/central-node/0",
        json_factory("command_assign_resource_low"),
        json_factory("command_release_resource_low"),
        change_event_callbacks,
    )

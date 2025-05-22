"""Test module for assign resources unavailability"""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common.dev_factory import DevFactory
from tango.db import Database

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
)
from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    LOW_SUBARRAY_DEVICE,
    MID_SUBARRAY_DEVICE,
    add_device_to_db,
    check_subarray_availability,
    logger,
)


def assign_resources(
    tango_context,
    central_node_fqdn,
    assign_input_str,
    change_event_callbacks,
    subarray_fqdn,
):
    """Assign Resources command method."""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node_proxy = dev_factory.get_device(central_node_fqdn)
    subarray_proxy = dev_factory.get_device(subarray_fqdn)
    subarray_device = tango.DeviceProxy("dserver/mocks/03")

    ensure_checked_devices(central_node_proxy)

    result, unique_id = central_node_proxy.TelescopeOn()
    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    central_node_proxy.subscribe_event(
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
    check_subarray_availability(central_node_proxy, subarray_fqdn, True)

    subarray_proxy.SetisSubarrayAvailable(False)
    check_subarray_availability(central_node_proxy, subarray_fqdn, False)

    db = Database()
    db.delete_device(subarray_fqdn)

    # Waiting for event from central node

    if "mid-tmc" in central_node_fqdn:
        result, unique_id = central_node_proxy.AssignResources(
            assign_input_str
        )
    else:
        result, unique_id = central_node_proxy.AssignResources(
            assign_input_str
        )
    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    # assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.QUEUED
    logger.info(
        "Central_node ResultCode: %s",
        central_node_proxy.longRunningCommandResult,
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id[0],
            json.dumps(
                (
                    int(ResultCode.REJECTED),
                    "Exception from 'is_cmd_allowed' method: "
                    f"Subarray devices not available: ['{subarray_fqdn}']",
                )
            ),
        ),
        lookahead=4,
    )
    subarray_device.RestartServer()
    subarray_proxy.SetDirectObsState(ObsState.EMPTY)
    subarray_proxy.SetisSubarrayAvailable(True)

    add_device_to_db(
        device_name=subarray_fqdn,
        server_name="mocks/03",
        class_name="CNHelperSubArrayDevice",
    )
    subarray_device.RestartServer()

    # Teardown
    result, unique_id = central_node_proxy.TelescopeOff()


@pytest.mark.skip(
    reason="This functionality is not present in the current version"
)
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_assign_res_command_mid_unavailable_subarray(
    tango_context, central_node_name, change_event_callbacks, json_factory
):
    """Test Assign Resources command for low unavailable subarray for mid"""
    return assign_resources(
        tango_context,
        central_node_name,
        json_factory("command_AssignResources"),
        change_event_callbacks,
        MID_SUBARRAY_DEVICE,
    )


@pytest.mark.test1
@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_LOW],
)
def test_assign_res_command_low_unavailable_subarray(
    tango_context, central_node_name, change_event_callbacks, json_factory
):
    """Test Assign Resources command for low unavailable subarray"""
    return assign_resources(
        tango_context,
        central_node_name,
        json_factory("assign_resource_low"),
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
    )

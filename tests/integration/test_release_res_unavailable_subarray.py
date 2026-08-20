"""Test cases for release resources command"""

import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from tango.db import Database

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
)
from tests.integration.conftest import get_cn_sn
from tests.settings import (
    LOW_SUBARRAY_NOT_AVAILABLE,
    MID_SUBARRAY_NOT_AVAILABLE,
    assert_exception,
    assign_resources,
    check_subarray_availability,
    export_device,
    logger,
    telescope_off,
    telescope_on,
)


def release_resources_unavailable_subarray(
    central_node_fqdn,
    assign_input_str,
    release_input_string,
    change_event_callbacks,
):
    """Release Resources method for command invocation."""
    central_node, subarray_proxy, _ = get_cn_sn(central_node_fqdn)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)
    assign_resources(central_node, assign_input_str, change_event_callbacks)

    subarray_proxy.SetisSubarrayAvailable(False)
    check_subarray_availability(central_node, subarray_proxy.dev_name(), False)

    db = Database()
    db_device_info = db.get_device_info(subarray_proxy.dev_name())
    db.unexport_device(subarray_proxy.dev_name())

    # Waiting for event from central node
    time.sleep(3)

    result, unique_id = central_node.ReleaseResources(release_input_string)

    assert result[0] == ResultCode.QUEUED

    msg = LOW_SUBARRAY_NOT_AVAILABLE
    if "mid-tmc" in central_node_fqdn:
        msg = MID_SUBARRAY_NOT_AVAILABLE
    assert_exception(unique_id, msg, change_event_callbacks)
    export_device(db, db_device_info)
    time.sleep(3)

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, subarray_proxy.dev_name(), True)

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
def test_release_res_command_mid(change_event_callbacks, json_factory):
    """Test release resources command mid"""
    return release_resources_unavailable_subarray(
        CENTRALNODE_MID,
        json_factory("command_AssignResources"),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_sdp_csp_mccs_admin_modes")
def test_release_res_command_low(change_event_callbacks, json_factory):
    """Test release resources command for low"""
    return release_resources_unavailable_subarray(
        CENTRALNODE_LOW,
        json_factory("assign_resource_low"),
        json_factory("release_resource_low"),
        change_event_callbacks,
    )

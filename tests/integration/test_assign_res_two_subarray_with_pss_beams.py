"""Test module for AssignResourcesLow command."""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import CENTRALNODE_LOW
from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    LOW_SUBARRAY2_DEVICE,
    LOW_SUBARRAY_DEVICE,
    check_subarray_availability,
    logger,
)


def assign_resources_low(
    tango_context,
    central_node_name,
    assign_input_str,
    release_input_string,
    pss_beams,
    change_event_callbacks,
    subarray_device,
    subarray2_device,
    second_assign_failed=True,
):
    """AssignResources Test method."""
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    subarray_proxy = dev_factory.get_device(subarray_device)
    subarray2_proxy = dev_factory.get_device(subarray2_device)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "Telescope On Command ID: %s Returned result: %s",
        unique_id,
        str(result),
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

    assign_input_str1 = assign_input_str
    assign_input = json.loads(assign_input_str)
    assign_input["subarray_id"] = 2
    assign_input["sdp"]["execution_block"]["eb_id"] = "eb-test-20220917-00000"
    assign_input["csp"]["pss"]["pss_beam_ids"] = pss_beams
    assign_input_str2 = json.dumps(assign_input)

    subarray_proxy.SetisSubarrayAvailable(True)
    subarray2_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, subarray_device, True)

    result1, unique_id1 = central_node.AssignResources(assign_input_str1)
    result2, unique_id2 = central_node.AssignResources(assign_input_str2)

    assert unique_id1[0].endswith("AssignResources")
    assert result1[0] == ResultCode.QUEUED

    assert unique_id2[0].endswith("AssignResources")
    assert result2[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id1[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    if second_assign_failed:
        change_event_callbacks.assert_change_event(
            "longRunningCommandResult",
            (
                unique_id2[0],
                json.dumps(
                    (
                        int(ResultCode.FAILED),
                        f"PSS beams: {pss_beams} already"
                        " assigned to another subarray",
                    )
                ),
            ),
            lookahead=4,
        )
    else:
        change_event_callbacks.assert_change_event(
            "longRunningCommandResult",
            (
                unique_id2[0],
                json.dumps((int(ResultCode.OK), "Command Completed")),
            ),
            lookahead=4,
        )

    release_input_string1 = release_input_string

    result1, unique_id1 = central_node.ReleaseResources(release_input_string1)

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id1[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    tmc_subarray = dev_factory.get_device(subarray_device)
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)

    result, unique_id = central_node.TelescopeOff()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name, input_json, pss_beams",
    [
        (CENTRALNODE_LOW, "assign_resource_low", [1, 2, 3]),
        (CENTRALNODE_LOW, "assign_resource_low", [1, 2, 4]),
        (CENTRALNODE_LOW, "assign_resource_low", [1]),
    ],
)
def test_assign_res_with_two_subarray_low_same_pss_beam(
    tango_context,
    central_node_name,
    input_json,
    pss_beams,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
    set_low_sdp_csp_mccs_admin_modes,
):
    """Test assign Resources command for low with same pss beams"""
    assign_resources_low(
        tango_context,
        central_node_name,
        json_factory(input_json),
        json_factory("release_resource_low"),
        pss_beams,
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
        LOW_SUBARRAY2_DEVICE,
        second_assign_failed=True,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name, input_json, pss_beams",
    [
        (CENTRALNODE_LOW, "assign_resource_low", [4, 5, 6]),
        (CENTRALNODE_LOW, "assign_resource_low", [4]),
    ],
)
def test_assign_res_with_two_subarray_low_different_pss_beam(
    tango_context,
    central_node_name,
    input_json,
    pss_beams,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
    set_low_sdp_csp_mccs_admin_modes,
):
    """Test assign Resources command for low with different pss beams"""
    assign_resources_low(
        tango_context,
        central_node_name,
        json_factory(input_json),
        json_factory("release_resource_low"),
        pss_beams,
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
        LOW_SUBARRAY2_DEVICE,
        second_assign_failed=False,
    )

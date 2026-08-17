"""Test module for AssignResourcesLow command."""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState

from ska_tmc_centralnode.utils.constants import CENTRALNODE_LOW
from tests.integration.conftest import get_cn_sn
from tests.settings import telescope_off, telescope_on


def assign_resources_low(
    central_node_name,
    assign_input_str,
    release_input_string,
    pss_beams,
    change_event_callbacks,
    second_assign_rejected=True,
):
    """AssignResources Test method."""
    central_node, subarray_proxy, _ = get_cn_sn(central_node_name, 2)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    telescope_on(central_node, change_event_callbacks)

    assign_input_str1 = assign_input_str
    assign_input = json.loads(assign_input_str)
    assign_input["subarray_id"] = 2
    assign_input["sdp"]["execution_block"]["eb_id"] = "eb-test-20220917-00001"
    assigned_pss_beams = assign_input["csp"]["pss"]["pss_beam_ids"]
    assign_input["csp"]["pss"]["pss_beam_ids"] = pss_beams
    assign_input_str2 = json.dumps(assign_input)

    result1, unique_id1 = central_node.AssignResources(assign_input_str1)
    result2, unique_id2 = central_node.AssignResources(assign_input_str2)

    assert unique_id1[0].endswith("AssignResources")
    assert result1[0] == ResultCode.QUEUED
    if second_assign_rejected:
        assert result2[0] == ResultCode.REJECTED
        conflicting_pss_beams = list(
            set(pss_beams).intersection(assigned_pss_beams)
        )
        assert unique_id2[0] == (
            f"PSS beams: {conflicting_pss_beams} already "
            "assigned to another subarray"
        )
    else:
        assert unique_id2[0].endswith("AssignResources")
        assert result2[0] == ResultCode.QUEUED

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id1[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    if not second_assign_rejected:
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                unique_id2[0],
                json.dumps((int(ResultCode.OK), "Command Completed")),
            ),
            lookahead=4,
        )

    release_input_string1 = release_input_string
    release_input = json.loads(release_input_string)
    result1, unique_id1 = central_node.ReleaseResources(release_input_string1)

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id1[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    if not second_assign_rejected:
        release_input["subarray_id"] = 2
        release_input_string2 = json.dumps(release_input)
        result2, unique_id2 = central_node.ReleaseResources(
            release_input_string2
        )
        change_event_callbacks["longRunningCommandResult"].assert_change_event(
            (
                unique_id2[0],
                json.dumps((int(ResultCode.OK), "Command Completed")),
            ),
            lookahead=4,
        )
    subarray_proxy.SetDirectObsState(ObsState.EMPTY)

    telescope_off(central_node, change_event_callbacks)


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
@pytest.mark.usefixtures(
    "set_low_devices_availability_for_aggregation",
    "set_low_sdp_csp_mccs_admin_modes",
)
def test_assign_res_with_two_subarray_low_same_pss_beam(
    central_node_name,
    input_json,
    pss_beams,
    change_event_callbacks,
    json_factory,
):
    """Test assign Resources command for low with same pss beams"""
    assign_resources_low(
        central_node_name,
        json_factory(input_json),
        json_factory("release_resource_low"),
        pss_beams,
        change_event_callbacks,
        second_assign_rejected=True,
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
@pytest.mark.usefixtures(
    "set_low_devices_availability_for_aggregation",
    "set_low_sdp_csp_mccs_admin_modes",
)
def test_assign_res_with_two_subarray_low_different_pss_beam(
    central_node_name,
    input_json,
    pss_beams,
    change_event_callbacks,
    json_factory,
):
    """Test assign Resources command for low with different pss beams"""
    assign_resources_low(
        central_node_name,
        json_factory(input_json),
        json_factory("release_resource_low"),
        pss_beams,
        change_event_callbacks,
        second_assign_rejected=False,
    )

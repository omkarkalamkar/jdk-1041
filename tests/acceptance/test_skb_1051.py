"""Test cases for centralnode command"""

# pylint:disable=redefined-outer-name
import json

import pytest
import tango
from pytest_bdd import given, parsers, scenarios, then, when
from ska_control_model import AdminMode
from ska_tango_base.commands import ResultCode
from tango import DeviceProxy

from tests.settings import (
    LOW_CENTRAL_NODE,
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SUBARRAY2_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_MLN_DEVICE,
    assign_resources,
    check_subarray_availability,
    logger,
)


def subscribe_mccs_lrc_event():
    """subscribe event"""
    pytest.unique_id1 = None
    pytest.unique_id2 = None
    pytest.mccs_release1 = False
    pytest.mccs_release2 = False

    def cb(event):
        unique_id, result = event.attr_value.value
        logger.info(
            "MCCS long running command result event received: %s, %s",
            unique_id,
            result,
        )
        if unique_id.endswith("ReleaseAllResources") and result == json.dumps(
            [ResultCode.OK, "Command Completed"]
        ):
            if pytest.unique_id1 is None:
                pytest.unique_id1 = unique_id
                pytest.mccs_release1 = True
            elif unique_id != pytest.unique_id1:
                pytest.unique_id2 = unique_id
                pytest.mccs_release2 = True

    mccs_master_proxy = DeviceProxy(MCCS_MLN_DEVICE)
    pytest.sub_id = mccs_master_proxy.subscribe_event(
        "longrunningcommandresult", tango.EventType.CHANGE_EVENT, cb
    )
    pytest.mccs_master_proxy = mccs_master_proxy


@given(
    parsers.parse("a CentralNode Low device"),
    target_fixture="central_node",
)
def central_node():
    """Central node device"""
    central_node = DeviceProxy(LOW_CENTRAL_NODE)
    csp_proxy = DeviceProxy(LOW_CSP_MLN_DEVICE)
    sdp_proxy = DeviceProxy(LOW_SDP_MLN_DEVICE)
    mccs_proxy = DeviceProxy(MCCS_MLN_DEVICE)
    csp_proxy.SetCspControllerAdminMode(AdminMode.ONLINE)
    sdp_proxy.SetSdpControllerAdminMode(AdminMode.ONLINE)
    mccs_proxy.SetMccsControllerAdminMode(AdminMode.ONLINE)
    return central_node


@given("assigned two subarrays to the central node")
def invoke_assignresources_on_subarrays(
    central_node,
    json_factory,
    change_event_callbacks,
):
    """Method invokes assign resources on two subarrays."""
    subscribe_mccs_lrc_event()
    subarray_proxy = DeviceProxy(LOW_SUBARRAY_DEVICE)
    subarray_proxy.SetisSubarrayAvailable(True)
    subarray_proxy2 = DeviceProxy(LOW_SUBARRAY2_DEVICE)
    subarray_proxy2.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)
    check_subarray_availability(central_node, LOW_SUBARRAY2_DEVICE, True)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    assign_res_string = json_factory("assign_resource_low")
    assign_data = json.loads(assign_res_string)
    assign_resources(central_node, assign_res_string, change_event_callbacks)

    assign_data["subarray_id"] = 2
    # pss_beam_ids can not be shared between subarrays
    assign_data["csp"]["pss"]["pss_beam_ids"] = [4, 5, 6]
    assign_res_string = json.dumps(assign_data)
    assign_resources(central_node, assign_res_string, change_event_callbacks)


@when("resources are released from both the subarrays")
def invoke_release_resources_subarray(
    central_node, json_factory, change_event_callbacks
):
    """Method invokes release resources on two subarrays."""

    release_resource_string = json_factory("release_resource_low")
    release_resource_data = json.loads(release_resource_string)

    _, unique_id = central_node.ReleaseResources(release_resource_string)
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps([ResultCode.OK, "Command Completed"])),
        lookahead=10,
    )

    release_resource_data["subarray_id"] = 2
    release_resource_string = json.dumps(release_resource_data)
    _, unique_id = central_node.ReleaseResources(release_resource_string)
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps([ResultCode.OK, "Command Completed"])),
        lookahead=15,
    )


@then("the command is executed successfully on both the subarrays")
def verify_subarraynode():
    """Method verifies if release was invoked on subarray node"""
    subarray_proxy = DeviceProxy(LOW_SUBARRAY_DEVICE)
    subarray_proxy2 = DeviceProxy(LOW_SUBARRAY2_DEVICE)
    assert subarray_proxy.commandCallInfo[-1][0] == "ReleaseAllResources"
    assert subarray_proxy2.commandCallInfo[-1][0] == "ReleaseAllResources"


@then(
    "the command is executed successfully on the mccs master leaf node twice"
)
def verify_mccs_master_leaf_node():
    """Method verifies if release was invoked on mccs master leaf node"""
    pytest.mccs_master_proxy.unsubscribe_event(pytest.sub_id)
    assert pytest.mccs_release1
    assert pytest.mccs_release2


scenarios(
    "../features/skb_1051_release_on_mccs_with_multiple_subarray.feature"
)

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.conftest import ensure_checked_devices
from tests.settings import logger


def release_resources(
    tango_context,
    central_node_name,
    assign_input_str,
    release_input_string,
    change_event_callbacks,
):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
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
        (unique_id_on[0], str(int(ResultCode.OK))),
        lookahead=2,
    )

    if "ska_mid" in central_node_name:
        result, unique_id_assign = central_node.AssignResources(
            json.dumps(assign_input_str)
        )
    else:
        result, unique_id_assign = central_node.AssignResources(
            assign_input_str
        )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id_assign[0], str(int(ResultCode.OK))),
        lookahead=4,
    )

    if "ska_mid" in central_node_name:
        result, unique_id = central_node.ReleaseResources(
            json.dumps(release_input_string)
        )
    else:
        result, unique_id = central_node.ReleaseResources(release_input_string)

    logger.info(f"Unique id:{unique_id[0]}")
    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_release_res_command_mid(
    tango_context, change_event_callbacks, json_factory
):
    return release_resources(
        tango_context,
        "ska_mid/tm_central/central_node",
        json_factory("command_AssignResources"),
        json_factory("command_ReleaseResources"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_release_res_command_low(
    tango_context, change_event_callbacks, json_factory
):
    return release_resources(
        tango_context,
        "ska_low/tm_central/central_node",
        json_factory("command_assign_resource_low"),
        json_factory("command_release_resource_low"),
        change_event_callbacks,
    )

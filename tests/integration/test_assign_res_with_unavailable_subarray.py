import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    LOW_SUBARRAY_DEVICE,
    MID_SUBARRAY_DEVICE,
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
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node_proxy = dev_factory.get_device(central_node_fqdn)
    subarray_proxy = dev_factory.get_device(subarray_fqdn)

    ensure_checked_devices(central_node_proxy)

    result, unique_id = central_node_proxy.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )

    subarray_proxy.SetisSubarrayAvailable(False)

    check_subarray_availability(central_node_proxy, subarray_fqdn, False)

    if "ska_mid" in central_node_fqdn:
        result, unique_id = central_node_proxy.AssignResources(
            assign_input_str
        )
    else:
        result, unique_id = central_node_proxy.AssignResources(
            assign_input_str
        )
    logger.info(
        f"AssignResources Command ID: {unique_id} Returned result: {result}"
    )

    # assert unique_id[0].endswith("AssignResources")
    assert result[0] == ResultCode.REJECTED

    subarray_proxy.SetDirectObsState(ObsState.EMPTY)

    # Teardown
    result, unique_id = central_node_proxy.TelescopeOff()


@pytest.mark.skip(
    reason="This functionality is not present in the current version"
)
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_assign_res_command_mid(
    tango_context, central_node_name, change_event_callbacks, json_factory
):
    return assign_resources(
        tango_context,
        central_node_name,
        json_factory("command_AssignResources"),
        change_event_callbacks,
        MID_SUBARRAY_DEVICE,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_low/tm_central/central_node")],
)
def test_assign_res_command_low(
    tango_context, central_node_name, change_event_callbacks, json_factory
):
    return assign_resources(
        tango_context,
        central_node_name,
        json_factory("command_assign_resource_low"),
        change_event_callbacks,
        LOW_SUBARRAY_DEVICE,
    )

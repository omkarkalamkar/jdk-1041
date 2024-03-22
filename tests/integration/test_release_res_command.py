"""Test cases for rlease resources command"""
import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    ERROR_PROPAGATION_DEFECT,
    LOW_CENTRAL_NODE,
    LOW_SUBARRAY_DEVICE,
    MID_SUBARRAY_DEVICE,
    RESET_DEFECT,
    TIMEOUT_DEFECT,
    check_subarray_availability,
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
    if "ska_mid" in central_node_name:
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
        (unique_id_on[0], str(int(ResultCode.OK))),
        lookahead=6,
    )

    subarray_proxy.SetisSubarrayAvailable(True)
    if "ska_mid" in central_node_name:
        check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)
    else:
        check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    if "ska_mid" in central_node_name:
        result, unique_id_assign = central_node.AssignResources(
            assign_input_str
        )
    else:
        result, unique_id_assign = central_node.AssignResources(
            assign_input_str
        )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id_assign[0], str(int(ResultCode.OK))),
        lookahead=6,
    )

    result, unique_id = central_node.ReleaseResources(release_input_string)

    logger.info(f"Unique id:{unique_id[0]}")
    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
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
        "ska_mid/tm_central/central_node",
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
        "ska_low/tm_central/central_node",
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
        (unique_id_on[0], str(int(ResultCode.OK))),
        lookahead=4,
    )

    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id_assign = central_node.AssignResources(assign_input_str)

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id_assign[0], str(int(ResultCode.OK))),
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

    logger.info(f"Unique id:{unique_id[0]}")
    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )

    result, unique_id = central_node.TelescopeOff()
    logger.info(
        f"TelescopeOff Command ID: {unique_id} Returned result: {result}"
    )
    assert unique_id[0].endswith("TelescopeOff")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_release_res_command_mid_without_subarray_id(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test cases for release resources command without subarray id in string"""
    return release_resources_without_subarray_id(
        tango_context,
        "ska_mid/tm_central/central_node",
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
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=5,
    )

    result, unique_id = central_node.AssignResources(
        json_factory("command_AssignResources")
    )

    logger.info(
        f"AssignResources Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
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
        f"ReleaseResources Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id[0],
            f"Exception occurred on device: {MID_SUBARRAY_DEVICE}:"
            + " Exception occurred, command failed.",
        ),
        lookahead=6,
    )
    tmc_subarray.SetDefective(RESET_DEFECT)
    # Tear Down
    tmc_subarray.ReleaseAllResources()
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)
    # Teardown
    result, unique_id = central_node.TelescopeOff()


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
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    subarray_proxy = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_proxy.SetisSubarrayAvailable(True)
    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=5,
    )

    result, unique_id = central_node.AssignResources(
        json_factory("command_AssignResources")
    )

    logger.info(
        f"AssignResources Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=6,
    )

    tmc_subarray = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    tmc_subarray.SetDefective(TIMEOUT_DEFECT)
    check_subarray_availability(central_node, MID_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_ReleaseResources")
    )

    logger.info(
        f"ReleaseResources Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id[0],
            "Timeout has occurred, command failed",
        ),
        lookahead=8,
    )
    tmc_subarray.SetDefective(RESET_DEFECT)
    tmc_subarray.ReleaseAllResources()
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)
    # Teardown
    result, unique_id = central_node.TelescopeOff()


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
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )

    result, unique_id = central_node.AssignResources(
        json_factory("command_assign_resource_low")
    )

    logger.info(
        f"AssignResources Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=6,
    )

    tmc_subarray = DevFactory().get_device(LOW_SUBARRAY_DEVICE)
    tmc_subarray.SetDefective(TIMEOUT_DEFECT)
    check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_release_resource_low")
    )

    logger.info(
        f"ReleaseResources Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id[0],
            "Timeout has occurred, command failed",
        ),
        lookahead=6,
    )
    tmc_subarray.SetDefective(RESET_DEFECT)
    tmc_subarray.SetDirectObsState(ObsState.EMPTY)
    # Teardown
    result, unique_id = central_node.TelescopeOff()


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_release_resources_error_aggregation(
    tango_context,
    change_event_callbacks,
    json_factory,
    set_low_devices_availability_for_aggregation,
):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(LOW_CENTRAL_NODE)
    subarray_proxy = dev_factory.get_device(LOW_SUBARRAY_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=5,
    )
    subarray_proxy.SetisSubarrayAvailable(True)
    check_subarray_availability(central_node, LOW_SUBARRAY_DEVICE, True)

    result, unique_id = central_node.AssignResources(
        json_factory("command_assign_resource_low")
    )

    logger.info(
        f"AssignResources Command ID: {unique_id} Returned result: {result}"
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
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=6,
    )

    subarray_proxy.SetDefective(ERROR_PROPAGATION_DEFECT)

    result, unique_id = central_node.ReleaseResources(
        json_factory("command_release_resource_low")
    )

    logger.info(
        f"ReleaseResources Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("ReleaseResources")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (
            unique_id[0],
            "Exception occurred on the following devices: "
            + LOW_SUBARRAY_DEVICE
            + ": Exception occurred, command failed.",
        ),
        lookahead=6,
    )
    subarray_proxy.SetDefective(RESET_DEFECT)
    # Teardown
    subarray_proxy.ReleaseAllResources()
    subarray_proxy.SetDirectObsState(ObsState.EMPTY)
    result, unique_id = central_node.TelescopeOff()

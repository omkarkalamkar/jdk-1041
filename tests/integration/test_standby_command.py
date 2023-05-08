import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from tests.integration.conftest import ensure_checked_devices
from tests.settings import logger

@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_standby_command_mid(tango_context, change_event_callbacks):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    # Check whether the command ResultCode is OK
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=8,
    )
    logger.info(
        f"longRunningCommandResult: {central_node.longRunningCommandResult}"
    )

    result, unique_id = central_node.TelescopeStandby()
    logger.info("Result is: %s", result)
    logger.info("Unique id: %s", unique_id)

    # Check whether the command is QUEUED
    assert unique_id[0].endswith("TelescopeStandby")
    assert result[0] == ResultCode.QUEUED

    # Check whether the command ResultCode is OK
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=3,
    )
    logger.info(
        f"longRunningCommandResult: {central_node.longRunningCommandResult}"
    )

    csp_master = dev_factory.get_device("mid-csp/control/0")
    csp_master.SetDirectState(DevState.STANDBY)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    # Check whether the telescopeState is STANDBY
    change_event_callbacks.assert_change_event(
        "telescopeState", DevState.STANDBY, lookahead=2
    )
    logger.info(f"telescopeState: {central_node.telescopeState}")

    assert central_node.telescopeState == DevState.STANDBY


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_standby_command_low(tango_context, change_event_callbacks):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_low/tm_central/central_node")
    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    # Check whether the command ResultCode is OK
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=8,
    )
    logger.info(
        f"longRunningCommandResult: {central_node.longRunningCommandResult}"
    )

    result, unique_id = central_node.TelescopeStandby()
    logger.info("Result is: %s. Unique ID is %s", result, unique_id)

    # Check whether the command is QUEUED
    assert unique_id[0].endswith("TelescopeStandby")
    assert result[0] == ResultCode.QUEUED

    # Check whether the command ResultCode is OK
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=3,
    )
    logger.info(
        f"longRunningCommandResult: {central_node.longRunningCommandResult}"
    )

    # mccs_master = dev_factory.get_device("low-mccs/control/control")
    # mccs_master.SetDirectState(DevState.STANDBY)

    csp_master = dev_factory.get_device("low-csp/control/0")
    csp_master.SetDirectState(DevState.STANDBY)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    # Check whether the telescopeState is STANDBY
    change_event_callbacks.assert_change_event(
        "telescopeState", DevState.STANDBY, lookahead=2
    )
    logger.info(f"telescopeState: {central_node.telescopeState}")

    assert central_node.telescopeState == DevState.STANDBY

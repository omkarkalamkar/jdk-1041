import time
import tango

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


def standby_command(tango_context, central_node_name, change_event_callbacks):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    ensure_checked_devices(central_node)
    
    result, unique_id = central_node.TelescopeOn()
    logger.info(f"telescopeState: {central_node.telescopeState}")
    logger.info(f"longRunningCommandStatus: {central_node.longRunningCommandStatus}")
    logger.info(f"longRunningCommandResult: {central_node.longRunningCommandResult}")
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
    logger.info(f"longRunningCommandResult: {central_node.longRunningCommandResult}")
    
    result, unique_id = central_node.TelescopeStandby()
    
    logger.info("Result is: %s", result)
    logger.info("Unique id: %s", unique_id)
    
    assert unique_id[0].endswith("TelescopeStandby")
    assert result[0] == ResultCode.QUEUED
    logger.info(f"longRunningCommandStatus: {(central_node.longRunningCommandStatus)}")
    for command in reversed(central_node.longRunningCommandStatus):
        logger.info(f"command: {command}")
        if unique_id[0] in command[0]:
            assert command[1] == 'IN_PROGRESS'
            break

        # think about else part
    
    logger.info(f"longRunningCommandResult: {central_node.longRunningCommandResult}")
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=3,
    )
    logger.info(f"longRunningCommandResult: {central_node.longRunningCommandResult}")

    csp_master = dev_factory.get_device("mid_csp/elt/master")
    csp_master.SetDirectState(DevState.STANDBY)
    mccs_master = dev_factory.get_device("low-mccs/control/control")
    mccs_master.SetDirectState(DevState.STANDBY)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", DevState.STANDBY, lookahead=2
    )
    logger.info(f"telescopeState: {central_node.telescopeState}")

    assert central_node.telescopeState == DevState.STANDBY


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_standby_command_mid(tango_context, change_event_callbacks):
    standby_command(tango_context, "ska_mid/tm_central/central_node", change_event_callbacks)


@pytest.mark.skip(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_standby_command_low(tango_context, change_event_callbacks):
    standby_command(tango_context, "ska_low/tm_central/central_node", change_event_callbacks)

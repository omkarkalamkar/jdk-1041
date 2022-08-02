import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import PointingState

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_on_command_mid(tango_context, change_event_callbacks):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    command_status_dict = {}
    command_status = central_node.longRunningCommandStatus
    logger.info(f"command_status: {command_status}, {len(command_status)}")
    for index in range(0, len(command_status)):
        logger.info(f"index: {index}")
        if index % 2 == 0:
            command_status_dict[command_status[index]] = command_status[
                index + 1
            ]

    logger.info(f"command_status_dict: {command_status_dict}")

    # Check whether the command status is IN_PROGRESS
    command_executed = False
    for command, status in reversed(list(command_status_dict.items())):
        logger.info(f"command: {command}, {status}")
        if unique_id[0] in command:
            command_executed = True
            assert status == "IN_PROGRESS"
            break
    assert command_executed is True, f"{command[0]} is not executed."

    # Check whether the command ResultCode is OK
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=3,
    )
    logger.info(
        f"longRunningCommandResult: {central_node.longRunningCommandResult}"
    )

    csp_master = dev_factory.get_device("mid_csp/elt/master")
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device("mid_sdp/elt/master")
    sdp_master.SetDirectState(tango.DevState.ON)

    dish_master = dev_factory.get_device("mid_d0001/elt/master")
    dish_master.SetDirectState(tango.DevState.ON)
    dish_master.SetDirectPointingState(PointingState.READY)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.ON, lookahead=2
    )
    assert central_node.telescopeState == tango.DevState.ON


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_on_command_low(tango_context, change_event_callbacks):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_low/tm_central/central_node")
    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    command_status_dict = {}
    command_status = central_node.longRunningCommandStatus
    logger.info(f"command_status: {command_status}, {len(command_status)}")
    for index in range(0, len(command_status)):
        logger.info(f"index: {index}")
        if index % 2 == 0:
            command_status_dict[command_status[index]] = command_status[
                index + 1
            ]
    logger.info(f"command_status_dict: {command_status_dict}")

    # Check whether the command status is IN_PROGRESS
    command_executed = False
    for command, status in reversed(list(command_status_dict.items())):
        logger.info(f"command: {command}, {status}")
        if unique_id[0] in command:
            command_executed = True
            assert status == "IN_PROGRESS"
            break
    assert command_executed is True, f"{command[0]} is not executed."

    # Check whether the command ResultCode is OK
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=3,
    )
    logger.info(
        f"longRunningCommandResult: {central_node.longRunningCommandResult}"
    )

    mccs_master = dev_factory.get_device("low-mccs/control/control")
    mccs_master.SetDirectState(tango.DevState.ON)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.ON, lookahead=2
    )
    assert central_node.telescopeState == tango.DevState.ON

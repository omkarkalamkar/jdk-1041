import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import PointingState

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)


def on_command(tango_context, centralnode_name, change_event_callbacks):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(centralnode_name)
    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandsInQueue"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandsInQueue", None
    )

    result, unique_id = central_node.TelescopeOn()

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandsInQueue", ("TelescopeOn",)
    )

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=2,
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
@pytest.mark.SKA_mid
def test_on_command_mid(tango_context, change_event_callbacks):
    on_command(
        tango_context,
        "ska_mid/tm_central/central_node",
        change_event_callbacks,
    )


@pytest.mark.skip(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_on_command_low(tango_context, change_event_callbacks):
    on_command(
        tango_context,
        "ska_low/tm_central/central_node",
        change_event_callbacks,
    )

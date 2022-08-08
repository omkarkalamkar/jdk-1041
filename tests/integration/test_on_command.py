import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import PointingState

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_on_command_mid(tango_context, change_event_callbacks):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()

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
        "telescopeState", tango._tango.DevState.ON, lookahead=4
    )
    assert central_node.telescopeState == tango.DevState.ON


@pytest.mark.skip()
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_on_command_low(tango_context, change_event_callbacks):
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_low/tm_central/central_node")
    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()

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
        lookahead=2,
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

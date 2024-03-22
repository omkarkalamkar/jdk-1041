"""Test cases for Off command"""
import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState

from tests.integration.conftest import ensure_checked_devices
from tests.settings import event_remover


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_off_command_mid(
    tango_context,
    change_event_callbacks,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test cases for Off command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    ensure_checked_devices(central_node)

    result_on, unique_id_on = central_node.TelescopeOn()
    assert result_on[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id_on[0], str(int(ResultCode.OK))),
        lookahead=4,
    )

    result_off, unique_id_off = central_node.TelescopeOff()
    assert result_off[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id_off[0], str(int(ResultCode.OK))),
        lookahead=6,
    )

    csp_master = dev_factory.get_device("mid-csp/control/0")
    csp_master.SetDirectState(tango.DevState.OFF)

    sdp_master = dev_factory.get_device("mid-sdp/control/0")
    sdp_master.SetDirectState(tango.DevState.OFF)

    dish_master = dev_factory.get_device("ska001/elt/master")
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dish_master.SetDirectPointingState(PointingState.READY)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.OFF, lookahead=6
    )
    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult", "telescopeState"],
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_off_command_low(
    tango_context,
    change_event_callbacks,
    set_low_devices_availability_for_aggregation,
):
    """Test cases for off command for low"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_low/tm_central/central_node")
    ensure_checked_devices(central_node)
    result_on, unique_id_on = central_node.TelescopeOn()
    result_off, unique_id_off = central_node.TelescopeOff()

    assert result_on[0] == ResultCode.QUEUED
    assert result_off[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id_on[0], str(int(ResultCode.OK))),
        lookahead=3,
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id_off[0], str(int(ResultCode.OK))),
        lookahead=3,
    )

    mccs_master = dev_factory.get_device("low-mccs/control/control")
    mccs_master.SetDirectState(tango.DevState.OFF)
    csp_master = dev_factory.get_device("low-csp/control/0")
    csp_master.SetDirectState(tango._tango.DevState.OFF)

    csp_master.subscribe_event(
        "State",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["State"],
    )
    change_event_callbacks.assert_change_event(
        "State",
        tango._tango.DevState.OFF,
        lookahead=5,
    )

    sdp_master = dev_factory.get_device("low-sdp/control/0")
    sdp_master.SetDirectState(tango._tango.DevState.OFF)

    sdp_master.subscribe_event(
        "State",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["State"],
    )
    change_event_callbacks.assert_change_event(
        "State",
        tango._tango.DevState.OFF,
        lookahead=3,
    )

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.OFF, lookahead=3
    )

    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult", "telescopeState", "State"],
    )

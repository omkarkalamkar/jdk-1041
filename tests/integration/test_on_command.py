"""Test cases for ON command"""
import pytest
import tango
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode, PointingState

from tests.integration.conftest import ensure_checked_devices
from tests.settings import event_remover


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_on_command_mid(
    tango_context,
    change_event_callbacks,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test cases for ON command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    assert central_node.HealthState == HealthState.OK
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
        lookahead=4,
    )

    csp_master = dev_factory.get_device("mid-csp/control/0")
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device("mid-sdp/control/0")
    sdp_master.SetDirectState(tango.DevState.ON)

    dish_master = dev_factory.get_device("ska001/elt/master")
    dish_master.SetDirectDishMode(DishMode.STANDBY_FP)
    dish_master.SetDirectPointingState(PointingState.READY)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.ON, lookahead=5
    )
    assert central_node.telescopeState == tango.DevState.ON
    # Teardown
    result, unique_id = central_node.TelescopeOff()
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )
    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult", "telescopeState"],
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_on_command_low(
    tango_context,
    change_event_callbacks,
    set_low_devices_availability_for_aggregation,
):
    """Test cases for ON command for low"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_low/tm_central/central_node")
    assert central_node.HealthState == HealthState.OK
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
        lookahead=4,
    )

    mccs_master = dev_factory.get_device("low-mccs/control/control")
    mccs_master.SetDirectState(tango.DevState.ON)

    csp_master = dev_factory.get_device("low-csp/control/0")
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device("low-sdp/control/0")
    sdp_master.SetDirectState(tango.DevState.ON)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.ON, lookahead=2
    )
    assert central_node.telescopeState == tango.DevState.ON

    # Teardown
    result, unique_id = central_node.TelescopeOff()
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=4,
    )
    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult", "telescopeState"],
    )

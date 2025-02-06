"""Test cases for ON command"""
import json

import pytest
import tango
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.enum import DishMode

from ska_tmc_centralnode.utils.constants import (
    DISH_LEAF_NODE_1,
    LOW_CSP_MASTER_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    MCCS_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_SDP_MASTER_DEVICE,
)
from tests.integration.conftest import ensure_checked_devices
from tests.settings import event_remover


# pylint:disable=c-extension-no-member
# this linting warning is suppressed cause its not able to recognise
# tango._tango.Devstate which is c-extension member
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_on_command_mid(
    tango_context,
    change_event_callbacks,
    set_mid_sdp_csp_mln_availability_for_aggregation,
):
    """Test cases for ON command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("mid-tmc/central-node/0")
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

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device(MID_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.ON)

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_1)
    dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )
    change_event_callbacks["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=2,
    )

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.ON, lookahead=12
    )
    assert central_node.telescopeState == tango.DevState.ON
    # Teardown
    result, unique_id = central_node.TelescopeOff()
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
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
    central_node = dev_factory.get_device("low-tmc/central-node/0")
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
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    mccs_master = dev_factory.get_device(MCCS_MASTER_DEVICE)
    mccs_master.SetDirectState(tango.DevState.ON)

    csp_master = dev_factory.get_device(LOW_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.ON)

    sdp_master = dev_factory.get_device(LOW_SDP_MASTER_DEVICE)
    sdp_master.SetDirectState(tango.DevState.ON)

    central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["telescopeState"],
    )

    change_event_callbacks.assert_change_event(
        "telescopeState", tango._tango.DevState.ON, lookahead=4
    )
    assert central_node.telescopeState == tango.DevState.ON

    # Teardown
    result, unique_id = central_node.TelescopeOff()
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult", "telescopeState"],
    )

"""Test Events on centralnode"""

import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_LOW,
    CENTRALNODE_MID,
    LOW_CSP_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
)
from tests.integration.conftest import ensure_checked_devices
from tests.settings import SLEEP_TIME, TIMEOUT, logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_internal_model_events_mid():
    """Test internal model events for mid."""
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_MID)

    event_id = central_node.subscribe_event(
        "lastDeviceInfoChanged",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    ensure_checked_devices(central_node)
    logger.debug(
        "central_node.lastDeviceInfoChanged: %s",
        central_node.lastDeviceInfoChanged,
    )

    csp_master = dev_factory.get_device(MID_CSP_MASTER_DEVICE)
    csp_master.SetDirectState(tango.DevState.STANDBY)
    time.sleep(0.1)
    logger.debug(
        "central_node.lastDeviceInfoChanged: %s",
        central_node.lastDeviceInfoChanged,
    )

    start_time = time.time()
    while pytest.num_events_arrived < 1:
        logger.info("waiting events: %s", pytest.num_events_arrived)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived >= 1
    central_node.unsubscribe_event(event_id)
    csp_master.SetDirectState(tango.DevState.ON)


@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_devices_availability_for_aggregation")
def test_internal_model_events_low():
    """Test internal model events for low"""
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(CENTRALNODE_LOW)

    event_id = central_node.subscribe_event(
        "lastDeviceInfoChanged",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    ensure_checked_devices(central_node)
    logger.debug(
        "central_node.lastDeviceInfoChanged: %s",
        central_node.lastDeviceInfoChanged,
    )

    mccs_master = dev_factory.get_device(LOW_CSP_MASTER_DEVICE)
    mccs_master.SetDirectState(tango.DevState.STANDBY)
    time.sleep(0.1)
    logger.debug(
        "central_node.lastDeviceInfoChanged: %s",
        central_node.lastDeviceInfoChanged,
    )

    start_time = time.time()
    while pytest.num_events_arrived < 1:
        logger.info("waiting events: %s", pytest.num_events_arrived)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived >= 1

    central_node.unsubscribe_event(event_id)


def commands_result_events(change_event_callbacks, central_node_name):
    """Test case for command result events"""

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    ensure_checked_devices(central_node)
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    _, unique_id = central_node.TelescopeOn()
    logger.info(
        "longRunningCommandResult: %s",
        str(central_node.longRunningCommandResult),
    )
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.usefixtures("set_mid_sdp_csp_mln_availability_for_aggregation")
def test_command_result_events_mid(
    change_event_callbacks,
):
    """Test command result events for mid."""
    commands_result_events(
        change_event_callbacks,
        CENTRALNODE_MID,
    )


@pytest.mark.skip(reason="Needs to be tested.")
@pytest.mark.post_deployment
@pytest.mark.SKA_low
@pytest.mark.usefixtures("set_low_sdp_csp_mln_availability_for_aggregation")
def test_command_result_events_low(
    change_event_callbacks,
):
    """Test command results event low"""
    commands_result_events(
        change_event_callbacks,
        CENTRALNODE_LOW,
    )

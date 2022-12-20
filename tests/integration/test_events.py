import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.conftest import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_internal_model_events_mid(tango_context, change_event_callbacks):
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

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

    csp_master = dev_factory.get_device("mid-csp/control/0")
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


@pytest.mark.skip(reason="Needs to be tested.")
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_internal_model_events_low(tango_context):
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_low/tm_central/central_node")

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

    mccs_master = dev_factory.get_device("low-mccs/control/control")
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


def commands_result_events(
    tango_context, change_event_callbacks, central_node_name
):
    logger.info("%s", tango_context)
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
        f"longRunningCommandResult: {central_node.longRunningCommandResult}"
    )
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=2,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_command_result_events_mid(tango_context, change_event_callbacks):
    commands_result_events(
        tango_context,
        change_event_callbacks,
        "ska_mid/tm_central/central_node",
    )


@pytest.mark.skip(reason="Needs to be tested.")
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_command_result_events_low(tango_context, change_event_callbacks):
    commands_result_events(
        tango_context,
        change_event_callbacks,
        "ska_low/tm_central/central_node",
    )

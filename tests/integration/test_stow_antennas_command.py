import time

import pytest
import tango
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.integration.common import (
    assert_events_arrived,
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


# @pytest.mark.xfail(reason="Need to debug")
@pytest.mark.post_deployment
def test_stow_antennas_command(tango_context):
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "InternalModel",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    ensure_checked_devices(central_node)
    initial_len = len(central_node.CommandExecuted)
    (result, unique_id) = central_node.On()
    (result, unique_id) = central_node.StowAntennas(["1"])
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.CommandExecuted) != initial_len + 2:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.CommandExecuted:
        if command[0] == unique_id[0]:
            logger.info("command result: %s", command)
            assert command[2] == "ResultCode.OK"

    assert_events_arrived()

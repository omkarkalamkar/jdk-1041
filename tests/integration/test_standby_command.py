import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


def standby_command(tango_context, central_node_name):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    ensure_checked_devices(central_node)
    initial_len = len(central_node.commandExecuted)
    (result, unique_id) = central_node.On()
    (result, unique_id) = central_node.Standby()
    logger.info("Result is: %s", result)
    logger.info("Unique id: %s", unique_id)
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.commandExecuted) != initial_len + 2:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.commandExecuted:
        if command[0] == unique_id[0]:
            if command[2] != "ResultCode.OK":
                logger.error("Message: %s", command[3])
            assert command[2] == "ResultCode.OK"

    csp_master = dev_factory.get_device("mid_csp/elt/master")
    csp_master.SetDirectState(DevState.STANDBY)
    mccs_master = dev_factory.get_device("low-mccs/control/control")
    mccs_master.SetDirectState(DevState.STANDBY)
    start_time = time.time()
    while central_node.telescopeState != DevState.STANDBY:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert central_node.telescopeState == DevState.STANDBY


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_standby_command_mid(tango_context):
    standby_command(tango_context, "ska_mid/tm_central/central_node")


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_standby_command_low(tango_context):
    standby_command(tango_context, "ska_low/tm_central/central_node")

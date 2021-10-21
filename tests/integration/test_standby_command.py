import time

import pytest
from ska_tango_base.commands import ResultCode
from tango import DevState

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


@pytest.mark.post_deployment
def test_standby_command(tango_context):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    ensure_checked_devices(central_node)
    initial_len = len(central_node.CommandExecuted)
    (result, unique_id) = central_node.On()
    (result, unique_id) = central_node.Standby()
    logger.info("Result is: %s", result)
    logger.info("Unique id: %s", unique_id)
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.CommandExecuted) != initial_len + 2:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.CommandExecuted:
        if command[0] == unique_id[0]:
            if command[2] != "ResultCode.OK":
                logger.error("Message: %s", command[3])
            assert command[2] == "ResultCode.OK"

    csp_master = dev_factory.get_device("mid_csp/elt/master")
    csp_master.SetDirectState(DevState.STANDBY)
    # sdp_master = dev_factory.get_device("mid_sdp/elt/master")
    # sdp_master.SetDirectState(DevState.STANDBY)
    # dish_master.SetDirectState(DevState.STANDBY)
    # dish_master = dev_factory.get_device("mid_d0001/elt/master")

    start_time = time.time()
    while central_node.telescopeState != DevState.STANDBY:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert central_node.telescopeState == DevState.STANDBY

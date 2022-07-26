import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import logger


def off_command(tango_context, centralnode_name):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(centralnode_name)
    ensure_checked_devices(central_node)
    logger.info(
        f"Before TelescopeOff longRunningCommandsInQueue attribute value is:::{central_node.longRunningCommandsInQueue}"
    )
    result, unique_id = central_node.TelescopeOff()
    logger.info(f"Command ID: {unique_id} Returned result: {result}")
    logger.info(
        f"After TelescopeOff longRunningCommandIDsInQueue attribute value is:::{central_node.longRunningCommandIDsInQueue}"
    )
    assert result[0] == ResultCode.QUEUED
    logger.info(
        f"After TelescopeOff longRunningCommandsInQueue attribute value is:::{central_node.longRunningCommandsInQueue}"
    )
    time.sleep(30)
    command_id, result = central_node.longRunningCommandResult
    logger.info(
        f"After TelescopeOff central_node.longRunningCommandResult:::::::{central_node.longRunningCommandResult}"
    )
    if command_id == unique_id[0]:
        logger.info(f"command:::::::{command_id}")
        assert result == "0"

    # initial_len = len(central_node.commandExecuted)
    # (result, unique_id) = central_node.On()
    # (result, unique_id) = central_node.Off()
    # logger.info(result)
    # logger.info(unique_id)
    # assert result[0] == ResultCode.QUEUED
    # start_time = time.time()
    # while len(central_node.commandExecuted) != initial_len + 2:
    #     time.sleep(SLEEP_TIME)
    #     elapsed_time = time.time() - start_time
    #     if elapsed_time > TIMEOUT:
    #         pytest.fail("Timeout occurred while executing the test")

    # for command in central_node.commandExecuted:
    #     if command[0] == unique_id[0]:
    #         assert command[2] == "ResultCode.OK"


# @pytest.mark.xfail(
#     reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
# )
# @pytest.mark.post_deployment
@pytest.mark.offp
def test_off_command_mid(tango_context):
    off_command(tango_context, "ska_mid/tm_central/central_node")


# @pytest.mark.xfail(
#     reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
# )
# @pytest.mark.post_deployment
@pytest.mark.offp
def test_off_command_low(tango_context):
    off_command(tango_context, "ska_low/tm_central/central_node")

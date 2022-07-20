import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.integration.common import (  # noqa F401
    devices_to_load,
    ensure_checked_devices,
)
from tests.settings import logger


def on_command(tango_context, centralnode_name):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(centralnode_name)
    ensure_checked_devices(central_node)
    logger.info(
        f"Before TelescopeOn longRunningCommandsInQueue attribute value is:::{central_node.longRunningCommandsInQueue}"
    )
    result, unique_id = central_node.TelescopeOn()
    logger.info(f"Command ID: {unique_id} Returned result: {result}")
    logger.info(
        f"After TelescopeOn longRunningCommandIDsInQueue attribute value is:::{central_node.longRunningCommandIDsInQueue}"
    )
    assert result[0] == ResultCode.QUEUED
    logger.info(
        f"After TelescopeOn longRunningCommandsInQueue attribute value is:::{central_node.longRunningCommandsInQueue}"
    )
    time.sleep(30)
    command_id, result = central_node.longRunningCommandResult
    logger.info(
        f"After TelescopeOn central_node.longRunningCommandResult:::::::{central_node.longRunningCommandResult}"
    )
    if command_id == unique_id[0]:
        logger.info(f"command:::::::{command_id}")
        assert result == "0"


@pytest.mark.ncra
# @pytest.mark.xfail(
#     reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
# )
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_on_command_mid(tango_context):
    on_command(tango_context, "ska_mid/tm_central/central_node")


@pytest.mark.xfail(
    reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring."
)
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_on_command_low(tango_context):
    on_command(tango_context, "ska_low/tm_central/central_node")

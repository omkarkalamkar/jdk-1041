import time

import pytest
import tango
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.integration.common import devices_to_load, ensure_checked_devices
from tests.settings import SLEEP_TIME, TIMEOUT, logger


@pytest.mark.post_deployment
def test_init_command(tango_context):
    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    ensure_checked_devices(central_node)

    result, _ = central_node.Init()
    assert result[0] == ResultCode.OK
    assert len(central_node.CommandExecuted) == 1
    for command in central_node.CommandExecuted:
        if command[0] == "0":
            assert command[1] == "Init"
            assert command[2] == "ResultCode.OK"

    ensure_checked_devices(central_node)

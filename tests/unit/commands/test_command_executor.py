import time

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.obs.obs_device import SKAObsDevice
from test_cm_all_working import create_cm

from ska_tmc_centralnode_mid.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode_mid.manager.adapters import (
    BaseAdapter,
    DishAdapter,
    SubArrayAdapter,
)
from ska_tmc_centralnode_mid.manager.command_executor import CommandExecutor
from tests.helper_adapter_factory import HelperAdapterFactory
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    DEVICE_LIST,
    SLEEP_TIME,
    TIMEOUT,
    count_faulty_devices,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [{"name": "ska_mid/tm_subarray_node/1"}],
        },
        {
            "class": SKAObsDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def test_command_executor(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    executor = CommandExecutor(logger)
    my_adapter_factory = HelperAdapterFactory()
    on_command = TelescopeOn(cm, cm.op_state_model, my_adapter_factory)
    executor.enqueue_command(on_command, None)
    executor.enqueue_command(on_command, None)
    executor.enqueue_command(on_command, None)
    start_time = time.time()
    while 3 != len(executor.command_executed):
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        time.sleep(SLEEP_TIME)

    for command_result in executor.command_executed:
        assert command_result["Command"] == "TelescopeOn"
        assert command_result["ResultCode"] == ResultCode.OK
        assert command_result["Message"] == ""

def test_command_executor_raise_exception(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    executor = CommandExecutor(logger)
    attrs = {"do.side_effect": Exception}
    on_command = mock.Mock(**attrs)
    executor.enqueue_command(on_command, None)
    start_time = time.time()
    while 1 != len(executor.command_executed):
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        time.sleep(SLEEP_TIME)

    for command_result in executor.command_executed:
        assert command_result["Command"] == "Mock"
        assert command_result["ResultCode"] == ResultCode.FAILED


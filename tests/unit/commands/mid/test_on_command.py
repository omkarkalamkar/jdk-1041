import time

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)
from tango import DevState

from tests.mock_callable import MockCallable
from tests.settings import create_cm, logger


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [{"name": "ska_mid/tm_subarray_node/1"}],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def test_telescope_on_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)
    cm.is_command_allowed("TelescopeOn")
    cm.telescope_on(task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED


def test_telescope_on_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.timeout = 0
    assert cm.is_command_allowed("TelescopeOn")

    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)
    cm.telescope_on(task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.FAILED


def test_telescope_on_fail_check_allowed(tango_context):

    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.DISABLE
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("TelescopeOn")

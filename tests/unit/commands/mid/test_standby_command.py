import time

import mock
import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)
from tango import DevState

from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
)
from tests.mock_callable import MockCallable
from tests.settings import create_cm_mid, logger


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


# Modified the TelescopeStandby integration test as per latest base classes.
# Review is expected for below tests.


def test_telescope_standby_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm_mid()
    # num_faulty = count_faulty_devices(cm)
    # assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)
    cm.is_command_allowed("TelescopeStandby")
    cm.telescope_standby(task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED


def test_telescope_standby_command_task_completed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm_mid()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("TelescopeStandby")
    my_adapter_factory = HelperAdapterFactory()

    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)

    standby_command = TelescopeStandby(cm, my_adapter_factory, logger=logger)
    standby_command.telescope_standby(
        logger=logger, task_callback=task_callback
    )
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.COMPLETED


def test_telescope_standby_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm_mid()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("TelescopeStandby")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "ska_mid/tm_subarray_node/1"

    my_adapter_factory.get_or_create_adapter(
        failing_dev, attrs={"Standby.side_effect": Exception}
    )
    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)

    standby_command = TelescopeStandby(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    standby_command.telescope_standby(
        logger=logger, task_callback=task_callback
    )
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result == ResultCode.FAILED


def test_telescope_standby_command_fail_dish(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm_mid()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    cm.is_command_allowed("TelescopeStandby")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "ska_mid/tm_leaf_node/d0001"

    attrs = {"SetStandbyFPMode.side_effect": Exception}
    dishMasterLeafMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(
        failing_dev, proxy=dishMasterLeafMock
    )

    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)

    standby_command = TelescopeStandby(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    standby_command.telescope_standby(
        logger=logger, task_callback=task_callback
    )
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result == ResultCode.FAILED


def test_telescope_standby_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm_mid()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT

    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("TelescopeStandby")

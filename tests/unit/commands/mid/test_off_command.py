import time

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

from ska_tmc_centralnode.commands.telescope_off_command import TelescopeOff
from tests.mock_callable import MockCallable
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    create_cm,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": MID_SDP_MLN_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def test_telescope_off_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)
    cm.is_command_allowed("TelescopeOff")
    cm.telescope_off(task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED


def test_telescope_off_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("TelescopeOff")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeOff command
    failing_dev = "ska_mid/tm_subarray_node/1"

    my_adapter_factory.get_or_create_adapter(
        failing_dev, attrs={"TelescopeOff.side_effect": Exception}
    )
    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)

    off_command = TelescopeOff(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    off_command.telescope_off(logger=logger, task_callback=task_callback)
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result == ResultCode.FAILED


def test_telescope_off_command_task_completed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("TelescopeOff")
    my_adapter_factory = HelperAdapterFactory()

    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)

    off_command = TelescopeOff(cm, my_adapter_factory, logger=logger)
    off_command.telescope_off(logger=logger, task_callback=task_callback)
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.COMPLETED


def test_telescope_off_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("TelescopeOff")

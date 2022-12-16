import time

import pytest
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)
from tango import DevState

from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.mock_callable import MockCallable
from tests.settings import create_cm, logger


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [{"name": "ska_low/tm_subarray_node/1"}],
        },
        {
            "class": HelperMCCSStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
            ],
        },
    )


# Modified the TelescopeStandby integration test as per latest base classes.
# Review is expected for below tests.

@pytest.mark.skip()
def test_low_telescope_standby_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)
    cm.is_command_allowed("TelescopeStandby")
    cm.telescope_standby(task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED

@pytest.mark.skip()
def test_telescope_standby_command_task_completed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
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

@pytest.mark.skip()
def test_low_telescope_standby_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("TelescopeStandby")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in Standby command
    failing_dev = "ska_low/tm_subarray_node/1"

    my_adapter_factory.get_or_create_adapter(
        failing_dev, attrs={"Standby.side_effect": Exception}
    )

    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)

    standby_command = TelescopeStandby(cm, my_adapter_factory, logger=logger)
    standby_command.telescope_standby(
        logger=logger, task_callback=task_callback
    )
    assert task_callback.status == TaskStatus.FAILED

@pytest.mark.skip()
def test_low_telescope_standby_command_fail_mccs(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("TelescopeStandby")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "ska_low/tm_leaf_node/mccs_master"
    my_adapter_factory.get_or_create_adapter(
        failing_dev, attrs={"Standby.side_effect": Exception}
    )

    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)

    standby_command = TelescopeStandby(cm, my_adapter_factory, logger=logger)
    standby_command.telescope_standby(
        logger=logger, task_callback=task_callback
    )
    assert task_callback.status == TaskStatus.FAILED

@pytest.mark.skip()
def test_low_telescope_standby_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("TelescopeStandby")

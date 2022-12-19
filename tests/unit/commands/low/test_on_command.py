import time

import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)
from tango import DevState

from ska_tmc_centralnode.commands.telescope_on_command import TelescopeOn
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
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/csp_master"},
                {"name": "ska_low/tm_leaf_node/sdp_master"},
            ],
        },
    )


@pytest.mark.SKA_low
def test_low_telescope_on_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)
    cm.is_command_allowed("TelescopeOn")
    cm.telescope_on(task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED


@pytest.mark.SKA_low
def test_telescope_on_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("TelescopeOn")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeOn command
    failing_dev = "ska_low/tm_subarray_node/1"

    my_adapter_factory.get_or_create_adapter(
        failing_dev, attrs={"TelescopeOn.side_effect": Exception}
    )
    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)

    on_command = TelescopeOn(cm, my_adapter_factory, logger=logger)
    on_command.telescope_on(logger=logger, task_callback=task_callback)
    assert task_callback.status == TaskStatus.FAILED


@pytest.mark.SKA_low
def test_telescope_on_command_task_completed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("TelescopeOn")
    my_adapter_factory = HelperAdapterFactory()

    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)

    on_command = TelescopeOn(cm, my_adapter_factory, logger=logger)
    on_command.telescope_on(logger=logger, task_callback=task_callback)
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.COMPLETED


@pytest.mark.SKA_low
def test_low_telescope_on_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("TelescopeOn")

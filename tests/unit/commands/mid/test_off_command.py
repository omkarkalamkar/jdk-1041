import time
from unittest.mock import Mock

import mock
import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common import AdapterType
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_centralnode.refactored_commands.telescope_off import (
    TelescopeOffMid,
)
from ska_tmc_centralnode.utils.constants import MID_TMC_SUBARRAY
from tests.mock_callable import MockCallable
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
    check_cspmln_availability,
    check_sdpmln_availability,
    create_cm,
    logger,
)


def test_telescope_off_command(tango_context, set_mid_sdp_csp_admin_modes):
    """Test telescope Off command (happy path via component manager)."""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_mln.SetSubsystemAvailable(True)
    sdp_mln.SetSubsystemAvailable(True)
    check_cspmln_availability(cm, True)
    check_sdpmln_availability(cm, True)
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is True
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is True
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("TelescopeOff")
    cm.telescope_off(task_callback=task_callback)
    assert task_callback.status == TaskStatus.COMPLETED


def test_telescope_off_command_unavailability(
    tango_context, set_mid_sdp_csp_admin_modes
):
    """Test telescope Off with unavailable CSP/SDP returns OK."""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_mln.SetSubsystemAvailable(False)
    sdp_mln.SetSubsystemAvailable(False)
    check_cspmln_availability(cm, False)
    check_sdpmln_availability(cm, False)
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is False
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is False
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("TelescopeOff")

    cm.telescope_off(task_callback=task_callback)
    time.sleep(1)
    assert task_callback.result[0] == ResultCode.OK


def test_telescope_off_command_fail_subarray(
    tango_context, set_mid_sdp_csp_admin_modes
):
    """Test telescope Off fails when subarray adapter raises exception."""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_mln.SetSubsystemAvailable(True)
    sdp_mln.SetSubsystemAvailable(True)
    check_cspmln_availability(cm, True)
    check_sdpmln_availability(cm, True)
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is True
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is True
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("TelescopeOff")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeOff command for subarray
    failing_dev = MID_TMC_SUBARRAY
    subarray_adapter = my_adapter_factory.get_or_create_adapter(
        failing_dev, adapter_type=AdapterType.SUBARRAY
    )
    subarray_adapter.invoke_command = mock.Mock(side_effect=Exception("Subarray Off failed"))
    
    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)
    cm.adapter_factory = my_adapter_factory
    off_command = TelescopeOffMid(
        command_runtime_context=cm._get_telescope_off_context(),
        adapter_provider=my_adapter_factory,
        logger=logger,
    )
    off_command.execute(
        argin=None,
        task_callback=task_callback,
        task_abort_event=None,
    )

    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result[0] == ResultCode.FAILED


def test_telescope_off_command_task_completed(
    tango_context, set_mid_sdp_csp_admin_modes
):
    """Test telescope Off completes successfully with direct command."""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)
    csp_mln.SetSubsystemAvailable(True)
    sdp_mln.SetSubsystemAvailable(True)
    check_cspmln_availability(cm, True)
    check_sdpmln_availability(cm, True)
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is True
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is True

    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("TelescopeOff")
    my_adapter_factory = HelperAdapterFactory()

    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)

    off_command = TelescopeOffMid(
        command_runtime_context=cm._get_telescope_off_context(),
        adapter_provider=my_adapter_factory,
        logger=logger,
    )
    off_command.execute(
        argin=None,
        task_callback=task_callback,
        task_abort_event=None,
    )
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.COMPLETED


def test_telescope_off_fail_check_allowed(
    tango_context, set_mid_sdp_csp_admin_modes
):
    """Test telescope Off command not allowed in fault state."""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.config.op_state_model.perform_action("init_invoked")
    cm.config.op_state_model.perform_action("component_on")
    cm.config.op_state_model.perform_action("component_fault")
    cm.config.op_state_model.perform_action("init_completed")
    with pytest.raises(CommandNotAllowed):
        cm.is_dish_vcc_config_set = True
        cm.is_command_allowed("TelescopeOff")


def test_telescope_off_command_rejected(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    """Test telescope Off rejected when dish device is unresponsive."""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_info_dishln = cm.get_device(DISH_LEAF_NODE_DEVICE)
    dev_info_dishln.update_unresponsive(True)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("TelescopeOff")
    error_msg = r"'mid-tmc/leaf-node-dish/ska001'\] not available"
    with pytest.raises(Exception, match=error_msg):
        cm.cmd_allowed_validator.is_command_allowed_before_lrc_start(
            command_name="TelescopeOff"
        )


def test_telescope_off_command_fail_dish(
    tango_context, set_mid_sdp_csp_admin_modes
):
    """Test telescope Off fails when dish Off command raises exception."""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s",
        len(cm.checked_devices),
        elapsed_time,
    )

    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)

    csp_mln.SetSubsystemAvailable(True)
    sdp_mln.SetSubsystemAvailable(True)

    check_cspmln_availability(cm, True)
    check_sdpmln_availability(cm, True)

    assert cm.component.telescope_availability["csp_master_leaf_node"] is True
    assert cm.component.telescope_availability["sdp_master_leaf_node"] is True

    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("TelescopeOff")

    my_adapter_factory = HelperAdapterFactory()

    failing_dev = DISH_LEAF_NODE_DEVICE
    err_msg = "Error in calling Off command for dish devices"

    # The refactored CommandExecutor calls adapter.invoke_command().
    # Mock the adapter itself so the exception propagates through
    # BaseTMCCommand.execute() and is converted to FAILED.
    dish_adapter = my_adapter_factory.get_or_create_adapter(
        failing_dev,
        adapter_type=AdapterType.DISH,
    )

    dish_adapter.invoke_command = Mock(side_effect=Exception(err_msg))

    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)

    cm.adapter_factory = my_adapter_factory

    off_command = TelescopeOffMid(
        command_runtime_context=cm._get_telescope_off_context(),
        adapter_provider=my_adapter_factory,
        logger=logger,
    )

    off_command.execute(
        argin=None,
        task_callback=task_callback,
        task_abort_event=None,
    )

    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result[0] == ResultCode.FAILED
    assert err_msg in task_callback.result[1]

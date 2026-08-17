import time

import mock
import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_centralnode.commands.telescope_off_command import TelescopeOff
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
    # import debugpy; debugpy.debug_this_thread()
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


def test_telescope_off_command_fail_subarray(
    tango_context, set_mid_sdp_csp_admin_modes
):
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

    # include exception in TelescopeOff command
    failing_dev = MID_TMC_SUBARRAY
    attrs = {"TelescopeOff.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)

    my_adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)
    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)

    off_command = TelescopeOff(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    off_command.telescope_off(task_callback=task_callback)
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result[0] == ResultCode.FAILED


def test_telescope_off_command_task_completed(
    tango_context, set_mid_sdp_csp_admin_modes
):
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

    off_command = TelescopeOff(cm, my_adapter_factory, logger=logger)
    off_command.telescope_off(task_callback=task_callback)
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.COMPLETED


def test_telescope_off_fail_check_allowed(
    tango_context, set_mid_sdp_csp_admin_modes
):
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
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_info_dishln = cm.get_device(DISH_LEAF_NODE_DEVICE)
    dev_info_dishln.update_unresponsive(True)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("TelescopeOff")
    with pytest.raises(Exception) as exception:
        cm.is_command_allowed_before_lrc_start(command_name="TelescopeOff")
        assert "'mid-tmc/leaf-node-dish/ska001' not available" in str(
            exception
        )


def test_telescope_off_command_fail_dish(
    tango_context, set_mid_sdp_csp_admin_modes
):
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

    # Include exception in Off command
    failing_dev = DISH_LEAF_NODE_DEVICE
    err_msg = "Error in calling Off command for dish devices"
    attrs = {"Off.side_effect": Exception}
    dishMasterLeafMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(
        failing_dev, proxy=dishMasterLeafMock
    )
    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)

    off_command = TelescopeOff(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    off_command.telescope_off(task_callback=task_callback)
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result[0] == ResultCode.FAILED
    assert err_msg in task_callback.result[1]
    assert failing_dev in task_callback.result[1]

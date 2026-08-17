import time

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

from ska_tmc_centralnode.commands.telescope_on_command import TelescopeOn
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


def test_telescope_on_command(tango_context, set_mid_sdp_csp_admin_modes):
    """Test telescope On Command"""
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOn"
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
    cm.is_command_allowed("TelescopeOn")
    cm.telescope_on(task_callback=task_callback)
    assert task_callback.status == TaskStatus.COMPLETED


def test_telescope_on_command_unavailability(
    tango_context, set_mid_sdp_csp_admin_modes
):
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOn"
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
    cm.is_command_allowed("TelescopeOn")

    cm.telescope_on(task_callback=task_callback)
    time.sleep(1)
    assert task_callback.result[0] == ResultCode.OK


def test_telescope_on_command_fail_subarray(
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
    cm.is_command_allowed("TelescopeOn")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeOn command
    failing_dev = MID_TMC_SUBARRAY
    attrs = {"TelescopeOn.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)
    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)

    on_command = TelescopeOn(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    on_command.telescope_on(task_callback=task_callback)
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result[0] == ResultCode.FAILED


def test_telescope_on_command_task_completed(
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
    cm.is_command_allowed("TelescopeOn")
    my_adapter_factory = HelperAdapterFactory()

    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)

    on_command = TelescopeOn(cm, my_adapter_factory, logger=logger)
    on_command.telescope_on(task_callback=task_callback)
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.COMPLETED


def test_telescope_on_fail_check_allowed(
    tango_context, set_mid_sdp_csp_admin_modes
):
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.config.op_state_model.perform_action("component_fault")
    with pytest.raises(CommandNotAllowed):
        cm.is_dish_vcc_config_set = True
        cm.is_command_allowed("TelescopeOn")


def test_telescope_on_command_rejected(
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
    cm.is_command_allowed("TelescopeOn")
    with pytest.raises(Exception) as exception:
        cm.is_command_allowed_before_lrc_start(command_name="TelescopeOn")
        assert "'mid-tmc/leaf-node-dish/ska001' not available" in str(
            exception
        )


def test_telescope_on_command_fail_dish(
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
    cm.is_command_allowed("TelescopeOn")
    my_adapter_factory = HelperAdapterFactory()

    # Include exception in On command
    failing_dev = DISH_LEAF_NODE_DEVICE
    err_msg = "Error in calling SetStandbyFPMode()"
    attrs = {"On.side_effect": Exception}
    dishMasterLeafMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(
        failing_dev, proxy=dishMasterLeafMock, adapter_type=AdapterType.DISH
    )
    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)

    on_command = TelescopeOn(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    on_command.telescope_on(task_callback=task_callback)
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result[0] == ResultCode.FAILED
    assert err_msg in task_callback.result[1]
    assert failing_dev in task_callback.result[1]

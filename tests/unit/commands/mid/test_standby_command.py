import time

import mock
import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
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

# Modified the TelescopeStandby integration test as per latest base classes.
# Review is expected for below tests.


def test_telescope_standby_command(tango_context, set_mid_sdp_csp_admin_modes):
    logger.info("%s", tango_context)

    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeStandby"
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
    cm.is_command_allowed("TelescopeStandby")
    cm.telescope_standby(task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED


def test_telescope_standby_command_task_completed(
    tango_context, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
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


def test_telescope_standby_command_fail_subarray(
    tango_context, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
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
    cm.is_command_allowed("TelescopeStandby")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = MID_TMC_SUBARRAY
    attrs = {"Standby.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)
    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)

    standby_command = TelescopeStandby(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    standby_command.telescope_standby(
        logger=logger, task_callback=task_callback
    )
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result[0] == ResultCode.FAILED


def test_telescope_standby_command_fail_dish(
    tango_context, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
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
    cm.is_command_allowed("TelescopeStandby")
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command

    attrs = {"Off.side_effect": Exception}
    dishMasterLeafMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(
        DISH_LEAF_NODE_DEVICE, proxy=dishMasterLeafMock
    )

    unique_id = f"{time.time()}_TelescopeStandby"
    task_callback = MockCallable(unique_id)

    standby_command = TelescopeStandby(cm, my_adapter_factory, logger=logger)
    cm.adapter_factory = my_adapter_factory
    standby_command.telescope_standby(
        logger=logger, task_callback=task_callback
    )
    assert task_callback.status == TaskStatus.COMPLETED
    assert task_callback.result[0] == ResultCode.FAILED


def test_telescope_standby_fail_check_allowed(
    tango_context, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT

    with pytest.raises(CommandNotAllowed):
        cm.is_dish_vcc_config_set = True
        cm.is_command_allowed("TelescopeStandby")


def test_telescope_standby_command_rejected(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_info_dishln = cm.get_device(DISH_LEAF_NODE_DEVICE)
    dev_info_dishln.update_unresponsive(True)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("TelescopeStandby")
    cm.telescope_standby(task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    data = task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.REJECTED,
            "result": Anything,
            "exception": Anything,
        },
        lookahead=5,
    )
    assert ResultCode.REJECTED == data["result"][0]
    assert f"['{DISH_LEAF_NODE_DEVICE}'] not available" in data["result"][1]

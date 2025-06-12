import threading
import time

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.model.input import InputParameterLow
from ska_tmc_centralnode.utils.constants import LOW_TMC_SUBARRAY
from tests.mock_callable import MockCallable
from tests.settings import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MCCS_MLN_DEVICE,
    check_cspmln_availability,
    check_mccsmln_availability,
    check_sdpmln_availability,
    create_cm,
    logger,
)


def set_device_unresponsive(
    dev_info, max_attempts=16, interval=0.5, timeout=8.0
):
    """Set device unresponsive with retries"""
    attempts = [0]

    def attempt_unresponsive():
        attempts[0] += 1
        try:
            dev_info.update_unresponsive(True)
            return True
        except Exception:
            if attempts[0] >= max_attempts:
                raise TimeoutError(
                    f"Failed to set {dev_info.name} unresponsive after {max_attempts} attempts"
                )
            # Schedule next attempt
            timer = threading.Timer(interval, attempt_unresponsive)
            timer.start()
            return False

    attempt_unresponsive()

    start_time = time.time()
    while time.time() - start_time < timeout:
        if dev_info.is_unresponsive():
            return
        time.sleep(0.1)
    raise TimeoutError(
        f"Timeout waiting for {dev_info.name} to become unresponsive after {timeout}s"
    )


@pytest.mark.SKA_low
def test_low_telescope_off_command(tango_context, task_callback):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
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
    cm.is_command_allowed("TelescopeOff")
    cm.telescope_off(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "Command Completed"),
        }
    )


@pytest.mark.SKA_low
def test_telescope_off_command_unavailability(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOff"
    task_callback = MockCallable(unique_id)
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
    csp_mln.SetSubsystemAvailable(False)
    sdp_mln.SetSubsystemAvailable(False)
    mccs_mln.SetSubsystemAvailable(False)
    check_cspmln_availability(cm, False)
    check_sdpmln_availability(cm, False)
    check_mccsmln_availability(cm, False)
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is False
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is False
    assert (cm.component.telescope_availability)[
        "mccs_master_leaf_node"
    ] is False
    cm.is_command_allowed("TelescopeOn")

    cm.telescope_on(task_callback=task_callback)
    time.sleep(1)
    assert task_callback.result[0] == ResultCode.OK


@pytest.mark.SKA_low
def test_telescope_off_command_fail_subarray(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
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
    cm.is_command_allowed("TelescopeOff")
    adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeOff command
    failing_dev = LOW_TMC_SUBARRAY
    attrs = {"TelescopeOff.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)
    cm.adapter_factory = adapter_factory

    cm.telescope_off(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    callback_data = task_callback.assert_against_call(
        status=TaskStatus.COMPLETED
    )
    assert callback_data["result"][0] == ResultCode.FAILED


@pytest.mark.SKA_low
def test_low_telescope_off_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("TelescopeOff")


@pytest.mark.SKA_low
def test_telescope_off_command_rejected(tango_context, task_callback):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_info_dishln = cm.get_device(MCCS_MLN_DEVICE)
    set_device_unresponsive(dev_info_dishln)
    cm.is_command_allowed("TelescopeOff")
    cm.telescope_off(task_callback=task_callback)

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
    assert f"['{MCCS_MLN_DEVICE}'] not available" in data["result"][1]

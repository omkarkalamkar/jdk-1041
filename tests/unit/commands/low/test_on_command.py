import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.model.input import InputParameterLow
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


@pytest.mark.SKA_low
def test_low_telescope_on_command(tango_context, task_callback):
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
    csp_mln.SetisSubsystemAvailable(True)
    sdp_mln.SetisSubsystemAvailable(True)
    check_cspmln_availability(cm, True)
    check_sdpmln_availability(cm, True)
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is True
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is True
    cm.is_command_allowed("TelescopeOn")
    cm.telescope_on(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


@pytest.mark.test1
@pytest.mark.SKA_low
def test_telescope_on_command_unavailability(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
    csp_mln.SetisSubsystemAvailable(False)
    sdp_mln.SetisSubsystemAvailable(False)
    mccs_mln.SetisSubsystemAvailable(False)
    check_cspmln_availability(cm, False)
    check_sdpmln_availability(cm, False)
    check_mccsmln_availability(cm, False)
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is False
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is False
    assert (cm.component.telescope_availability)["_master_leaf_node"] is False
    cm.is_command_allowed("TelescopeOn")

    cm.telescope_on(task_callback=task_callback)
    time.sleep(1)
    assert task_callback.result == ResultCode.OK


@pytest.mark.SKA_low
def test_telescope_on_command_fail_subarray(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    csp_mln.SetisSubsystemAvailable(True)
    sdp_mln.SetisSubsystemAvailable(True)
    check_cspmln_availability(cm, True)
    check_sdpmln_availability(cm, True)
    assert (cm.component.telescope_availability)[
        "csp_master_leaf_node"
    ] is True
    assert (cm.component.telescope_availability)[
        "sdp_master_leaf_node"
    ] is True
    cm.is_command_allowed("TelescopeOn")
    adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeOn command
    failing_dev = "ska_low/tm_subarray_node/1"

    adapter_factory.get_or_create_adapter(
        failing_dev, attrs={"TelescopeOn.side_effect": Exception}
    )
    cm.adapter_factory = adapter_factory

    cm.telescope_on(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
    )


@pytest.mark.SKA_low
def test_low_telescope_on_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("TelescopeOn")

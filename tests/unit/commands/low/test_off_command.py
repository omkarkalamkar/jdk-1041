import time

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)
from tango import DevState

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    check_cspmln_availability,
    check_sdpmln_availability,
    create_cm,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [{"name": LOW_SUBARRAY_DEVICE}],
        },
        # {
        #     "class": HelperMCCSStateDevice,
        #     "devices": [
        #         {"name": "ska_low/tm_leaf_node/mccs_master"},
        #     ],
        # },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
                {"name": LOW_SDP_MLN_DEVICE},
            ],
        },
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
    cm.is_command_allowed("TelescopeOff")
    cm.telescope_off(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


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
    cm.is_command_allowed("TelescopeOff")
    adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeOff command
    failing_dev = "ska_low/tm_subarray_node/1"

    adapter_factory.get_or_create_adapter(
        failing_dev, attrs={"TelescopeOff.side_effect": Exception}
    )
    cm.adapter_factory = adapter_factory

    cm.telescope_off(task_callback=task_callback)
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

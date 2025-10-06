import json
import time

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_simulators.helper_adapter_factory import HelperAdapterFactory
from tango import DevState

from ska_tmc_centralnode.commands.release_resources_command_low import (
    ReleaseResourcesLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import LOW_SUBARRAY_DEVICE, TIMEOUT, create_cm, logger


@pytest.mark.SKA_low
def test_low_release_resources_command(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    cm.is_command_allowed("ReleaseResources")

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_device.SetDirectObsState(ObsState.IDLE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    cm.subsystems_to_config = ["mccs", "csp", "sdp"]

    release_input_str = json_factory("release_resource_low")
    cm.release_resources(release_input_str, task_callback=task_callback)
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
def test_low_release_resources_command_fail_subarray(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    cm.subsystems_to_config = ["mccs", "csp", "sdp"]
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    adapter_factory = HelperAdapterFactory()

    # include exception in ReleaseResources command
    attrs = {"ReleaseAllResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(
        LOW_SUBARRAY_DEVICE, proxy=subarrayMock
    )
    release_input_str = json_factory("release_resource_low")
    assign_res_command = ReleaseResourcesLow(
        cm, adapter_factory=adapter_factory, logger=logger
    )
    (res_code, _) = assign_res_command.do(release_input_str)
    assert res_code == ResultCode.FAILED


@pytest.mark.SKA_low
def test_low_release_resources_empty_input_json(
    tango_context, task_callback, set_low_sdp_csp_mccs_admin_modes
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    (res_code, _) = cm.release_resources("", task_callback=task_callback)
    assert res_code == TaskStatus.REJECTED


@pytest.mark.SKA_low
def test_low_release_resources_command_with_invalide_key(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    release_input_str = json_factory("invalid_key_ReleaseResources")
    (res_code, message) = cm.release_resources(
        release_input_str, task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert (
        "subarray_id key is not present in the input json argument" in message
    )


@pytest.mark.SKA_low
def test_low_release_resources_missing_subarray_id(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm()
    release_input_str = json_factory("release_resource_low")
    json_argument = json.loads(release_input_str)
    del json_argument["subarray_id"]

    (res_code, message) = cm.release_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert (
        "subarray_id key is not present in the input json argument" in message
    )


@pytest.mark.SKA_low
def test_low_release_resources_fail_check_allowed(
    tango_context, set_low_sdp_csp_mccs_admin_modes
):
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("ReleaseResources")


def check_if_subarray_is_available(cm):
    start_time = time.time()
    elapsed_time = 0
    while (cm.component.telescope_availability)["tmc_subarrays"][
        LOW_SUBARRAY_DEVICE
    ] is not True:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        exp = "Timeout occurred while checking the SubarrayNode availability."
        if elapsed_time > TIMEOUT:
            pytest.fail(exp)


@pytest.mark.SKA_low
def test_low_release_resources_raises_state_model_exception(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    cm.is_command_allowed("ReleaseResources")

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_device.SetDirectObsState(ObsState.EMPTY)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    release_input_str = json_factory("release_resource_low")
    cm.release_resources(release_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )

    data = task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.REJECTED,
            "result": Anything,
            "exception": Anything,
        }
    )
    assert ResultCode.REJECTED == data["result"][0]
    assert "ReleaseResources command not permitted" in data["result"][1]

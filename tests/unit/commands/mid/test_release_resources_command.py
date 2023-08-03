import json
import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DevFactory, FaultType
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.commands.release_resources_command import (
    ReleaseResources,
)
from ska_tmc_centralnode.model.input import InputParameterMid
from tests.settings import MID_SUBARRAY_DEVICE, TIMEOUT, create_cm, logger


def get_release_input_str(release_input_file="command_ReleaseResources.json"):
    path = join(
        dirname(__file__), "..", "..", "..", "data", release_input_file
    )
    with open(path, "r") as f:
        release_input_str = f.read()
    return release_input_str


def test_mid_release_resources_command_with_ok(tango_context, task_callback):
    cm, _ = create_cm()
    cm.is_command_allowed("ReleaseResources")
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    release_input_str = get_release_input_str()
    cm.release_resources(release_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


def test_mid_release_resources_command_fail_subarray(
    tango_context, task_callback
):
    cm, start_time = create_cm(_input_parameter=InputParameterMid(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    adapter_factory = HelperAdapterFactory()
    attrs = {"ReleaseAllResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(
        MID_SUBARRAY_DEVICE, proxy=subarrayMock
    )
    release_input_str = get_release_input_str()
    assign_res_command = ReleaseResources(cm, adapter_factory, logger=logger)
    (res_code, _) = assign_res_command.do(release_input_str)
    assert res_code == ResultCode.FAILED


def test_mid_release_resources_command_empty_input_json(
    tango_context, task_callback
):
    cm, _ = create_cm()
    cm.is_command_allowed("ReleaseResources")
    cm.release_resources("", task_callback=task_callback)
    (res_code, _) = cm.release_resources("")
    assert res_code == TaskStatus.REJECTED


def test_telescope_release_resources_fail_check_allowed(tango_context):
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("ReleaseResources")


def test_mid_release_resources_command_with_invalide_key(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    release_input_str = json_factory("invalid_key_ReleaseResources")
    # with pytest.raises(InvalidJSONError):
    result_code, message = cm.release_resources(
        release_input_str, task_callback=task_callback
    )
    assert result_code == TaskStatus.REJECTED


def test_release_resources_command_timeout(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    cm.command_timeout = 2
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    result = cm.is_command_allowed("ReleaseResources")
    logger.info(f"Command allowed result is: {result}")

    defect = {
        "enabled": True,
        "fault_type": FaultType.STUCK_IN_INTERMEDIATE_STATE,
        "error_message": "Command stuck in processing",
        "result": ResultCode.FAILED,
        "intermediate_state": ObsState.RESOURCING,
    }
    subarray_device = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetDefective(json.dumps(defect))

    release_input_str = get_release_input_str()

    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.release_resources(release_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED,
        result=ResultCode.FAILED,
        exception="Timeout has occured, command failed",
    )
    subarray_device.SetDefective(json.dumps({"enabled": False}))


def test_release_resources_exception_on_sn(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("ReleaseResources")
    defect = {
        "enabled": True,
        "fault_type": FaultType.COMMAND_NOT_ALLOWED,
        "error_message": "Command not allowed on leaf node.",
        "result": ResultCode.FAILED,
    }
    subarray_device = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetDefective(json.dumps(defect))
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    release_input_str = get_release_input_str()
    cm.release_resources(release_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
    )
    assert "Command not allowed on leaf node." in result["exception"]
    subarray_device.SetDefective(json.dumps({"enabled": False}))


def check_if_subarray_is_available(cm):
    start_time = time.time()
    elapsed_time = 0
    while (cm.component.telescope_availability)["tmc_subarrays"][
        MID_SUBARRAY_DEVICE
    ] is not True:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the SubarrayNode availability."
            )

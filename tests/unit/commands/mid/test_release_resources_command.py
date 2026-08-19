import json
import threading
import time
from os.path import dirname, join

import mock
import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common import DevFactory, FaultType
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.model.input import InputParameterMid
from ska_tmc_centralnode.refactored_commands.releaseresources import (
    ReleaseResourcesMid,
)
from ska_tmc_centralnode.utils.json_validator_decorator import (
    release_validate_json_args,
)
from tests.settings import MID_SUBARRAY_DEVICE, TIMEOUT, create_cm, logger


def get_release_input_str(release_input_file="command_ReleaseResources.json"):
    path = join(
        dirname(__file__), "..", "..", "..", "data", release_input_file
    )
    with open(path, "r") as f:
        release_input_str = f.read()
    return release_input_str


def test_mid_release_resources_command_with_ok(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("ReleaseResources")
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetDirectObsState(ObsState.IDLE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    release_input_str = get_release_input_str()
    cm.release_resources(
        release_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
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


def test_mid_release_resources_command_fail_subarray(
    tango_context, task_callback, json_factory, set_mid_sdp_csp_admin_modes
):
    cm, start_time = create_cm(_input_parameter=InputParameterMid(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetDirectObsState(ObsState.IDLE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    sub_mock = mock.Mock(
        **{"invoke_command.side_effect": Exception("command failed")}
    )
    attrs = {"get_or_create_adapter.return_value": sub_mock}

    helper_adapter_factory = mock.Mock(**attrs)

    # include exception in ReleaseResources command
    release_input_str = json_factory("release_resource_low")
    cm.adapter_factory = helper_adapter_factory
    cm.release_resources(
        release_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
    assert ResultCode.FAILED == result["result"][0]
    assert "command failed" in result["result"][1]


def test_mid_release_resources_command_empty_input_json(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("ReleaseResources")
    decorated = release_validate_json_args(cm.release_resources)

    result_code, message = decorated(cm, " ")

    assert result_code == [ResultCode.REJECTED]
    assert message[0] == "Malformed input JSON"


def test_telescope_release_resources_fail_check_allowed(
    tango_context, set_mid_sdp_csp_admin_modes
):
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_dish_vcc_config_set = True
        cm.is_command_allowed("ReleaseResources")


def test_mid_release_resources_command_with_invalide_key(
    tango_context, task_callback, json_factory, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    release_input_str = json_factory("invalid_key_ReleaseResources")
    # with pytest.raises(InvalidJSONError):
    decorated = release_validate_json_args(cm.release_resources)

    result_code, message = decorated(cm, release_input_str)

    assert result_code == [ResultCode.REJECTED]
    assert (
        "subarray_id key is not present in the input json argument"
        in message[0]
    )


def test_release_resources_command_timeout(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, start_time = create_cm()
    cm.command_timeout = 2
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
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
    subarray_device.SetDirectObsState(ObsState.IDLE)
    subarray_device.SetDefective(json.dumps(defect))

    release_input_str = get_release_input_str()

    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.release_resources(
        release_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.FAILED, "Timeout has occurred, command failed"),
    )
    subarray_device.SetDefective(json.dumps({"enabled": False}))


def test_release_resources_exception_on_sn(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("ReleaseResources")
    defect = {
        "enabled": True,
        "fault_type": FaultType.COMMAND_NOT_ALLOWED_BEFORE_QUEUING,
        "error_message": "Command not allowed on leaf node.",
        "result": ResultCode.FAILED,
    }
    subarray_device = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetDirectObsState(ObsState.IDLE)
    subarray_device.SetDefective(json.dumps(defect))
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    release_input_str = get_release_input_str()
    cm.release_resources(
        release_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(
        status=TaskStatus.COMPLETED,
    )
    assert ResultCode.FAILED == result["result"][0]
    assert "Command not allowed on leaf node." in result["result"][1]
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


def test_mid_release_resources_raises_state_model_exception(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("ReleaseResources")
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetDirectObsState(ObsState.EMPTY)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    release_input_str = get_release_input_str()
    cm.release_resources(
        release_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.REJECTED,
            "result": (
                ResultCode.NOT_ALLOWED,
                "ReleaseResources command not permitted in observation state 0",
            ),
        }
    )

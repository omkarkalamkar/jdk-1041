"""Test case file"""

import json
import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory, FaultType
from ska_tmc_common.device_info import SubArrayDeviceInfo
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command_mid import (
    AssignResourcesMid,
)
from tests.settings import MID_SUBARRAY_DEVICE, TIMEOUT, create_cm, logger


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    """Assign Input String"""
    path = join(dirname(__file__), "..", "..", "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def test_assign_resources_command_completed(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    """Tests assign Resources completed"""
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    result = cm.is_command_allowed("AssignResources")
    logger.info(f"Command allowed result is: {result}")

    assign_input_str = get_assign_input_str()

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)

    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.assign_resources(assign_input_str, task_callback=task_callback)
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
        },
        lookahead=5,
    )


def test_assign_resources_command_with_mkt_ids_completed(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    """test assign resources command with meerkat id"""
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    result = cm.is_command_allowed("AssignResources")
    logger.info(f"Command allowed result is: {result}")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["dish"]["receptor_ids"] = ["MKT001", "MKT002"]
    json_argument = json.dumps(json_argument)

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.assign_resources(json_argument, task_callback=task_callback)
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
        },
        lookahead=5,
    )


def test_assign_resources_exception_on_sn(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    """Tests assign resources exception on sn"""
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    defect = {
        "enabled": True,
        "fault_type": FaultType.COMMAND_NOT_ALLOWED_BEFORE_QUEUING,
        "error_message": "Command not allowed on leaf node.",
        "result": ResultCode.FAILED,
    }
    subarray_device = DevFactory().get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetDefective(json.dumps(defect))
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    assign_input_str = get_assign_input_str()
    cm.assign_resources(assign_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
    assert result["result"][0] == ResultCode.FAILED
    assert "Command not allowed on leaf node." in result["result"][1]
    subarray_device.SetDefective(json.dumps({"enabled": False}))


def test_assign_resources_command_missing_eb_id_key_and_processing_blocks(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    """Test Assign Resources command missing eb id"""
    logger.info("%s", tango_context)
    cm, _ = create_cm()

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["sdp"]["execution_block"]["eb_id"]
    del json_argument["sdp"]["processing_blocks"]
    json_argument = json.dumps(json_argument)
    res_code, message = cm.assign_resources(
        json_argument, task_callback=task_callback
    )
    assert (
        "JSON validation error: Validation"
        " 'Mid TMC assign resources 2.4'" in message
    )
    assert res_code == TaskStatus.REJECTED


def test_assign_resources_command_with_ok(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    cm.assign_resources(assign_input_str, task_callback=task_callback)
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
        },
        lookahead=5,
    )


def test_assign_resources_command_with_mkt_ids_ok(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["dish"]["receptor_ids"] = ["MKT001", "MKT002"]
    json_argument = json.dumps(json_argument)

    cm.assign_resources(json_argument, task_callback=task_callback)
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


def test_assign_resources_command_fail_subarray(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    adapter_factory = HelperAdapterFactory()

    # include exception in AssignResources command
    attrs = {"AssignResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(
        MID_SUBARRAY_DEVICE, proxy=subarrayMock
    )

    assign_input_str = get_assign_input_str()
    assign_res_command = AssignResourcesMid(
        cm, adapter_factory=adapter_factory, logger=logger
    )
    (res_code, _) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED


def test_telescope_assign_resources_command_empty_input_json(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    (res_code, _) = cm.assign_resources("", task_callback=task_callback)
    assert res_code == TaskStatus.REJECTED


def test_assign_resources_fail_check_allowed(
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
        cm.is_command_allowed("AssignResources")


def test_assign_resources_command_timeout(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    cm.command_timeout = 2
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    result = cm.is_command_allowed("AssignResources")
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

    assign_input_str = get_assign_input_str()

    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.assign_resources(assign_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.FAILED, "Timeout has occurred, command failed"),
    )
    subarray_device.SetDefective(json.dumps({"enabled": False}))


def test_assign_resources_command_already_assigned(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    adapter_factory = HelperAdapterFactory()

    assign_res_command = AssignResourcesMid(cm, adapter_factory, logger=logger)
    # SKA001 is assigned to Subarray1
    for devInfo in cm.devices:
        if isinstance(devInfo, SubArrayDeviceInfo):
            if devInfo.dev_name == MID_SUBARRAY_DEVICE:
                devInfo.resources.append("SKA001")
                logger.info("devInfo is: %s", devInfo.resources)

    # Invoke AssignResources to assign already allocated resource - dish0001
    assign_input_str = get_assign_input_str()
    (res_code, _) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED


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


def test_mid_assign_resources_raises_state_model_exception(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    subarray_device.SetDirectObsState(ObsState.READY)
    check_if_subarray_is_available(cm)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    cm.assign_resources(assign_input_str, task_callback=task_callback)
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
    assert "AssignResources command not permitted" in data["result"][1]

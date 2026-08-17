"""Test case file"""

import json
import threading
import time
from os.path import dirname, join
from unittest.mock import MagicMock

import mock
import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory, FaultType
from ska_tmc_common.device_info import SubArrayDeviceInfo
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_centralnode.commands.assign_resources_command_mid import (
    AssignResourcesMid,
)
from ska_tmc_centralnode.utils.json_validator_decorator import (
    assign_validate_json_args,
)
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_LEAF_NODE_DEVICE_099,
    DISH_LEAF_NODE_DEVICE_500,
    DISH_LEAF_NODE_DEVICE_999,
    DISH_VCC_VALIDATION_RESULT_STATUS,
    MID_SUBARRAY_DEVICE,
    TIMEOUT,
    create_cm,
    logger,
)

VALID_DISH_IDS = ["SKA999", "SKA500", "SKA099"]
VALID_DISH_LNS = [
    DISH_LEAF_NODE_DEVICE_500,
    DISH_LEAF_NODE_DEVICE_099,
    DISH_LEAF_NODE_DEVICE_999,
]

INVALID_DISH_IDS = ["SKA1000"]
MKT_DISH_IDS = ["MKT001", "MKT002"]


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
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    cm.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        MagicMock(return_value=DISH_VCC_VALIDATION_RESULT_STATUS)
    )
    cm.dish_vcc_validation_status = MagicMock(
        return_value=DISH_VCC_VALIDATION_RESULT_STATUS
    )
    cm._event_cb_manager.update_k_value_validation(
        DISH_LEAF_NODE_DEVICE, ResultCode.OK
    )
    result = cm.is_command_allowed("AssignResources")
    logger.info(f"Command allowed result is: {result}")
    cm.input_parameter.dish_leaf_node_dev_names = VALID_DISH_LNS
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["dish"]["receptor_ids"] = VALID_DISH_IDS
    json_argument = json.dumps(json_argument)
    _, message = cm.validate_assign_json(json_argument)
    assert message == ""
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)

    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.assign_resources(
        json_argument,
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
        },
        lookahead=5,
    )


def test_assign_resources_command_failure_with_incorrect_id(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    """Tests assign Resources completed"""
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
    json_argument["dish"]["receptor_ids"] = INVALID_DISH_IDS
    json_argument = json.dumps(json_argument)
    _, message = cm.validate_assign_json(json_argument)
    assert message == "The dish id SKA1000 is not of the correct length."


def test_assign_resources_command_with_mkt_ids_completed(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    """test assign resources command with meerkat id"""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    cm.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        MagicMock(return_value=DISH_VCC_VALIDATION_RESULT_STATUS)
    )
    cm.dish_vcc_validation_status = MagicMock(
        return_value=DISH_VCC_VALIDATION_RESULT_STATUS
    )
    cm._event_cb_manager.update_k_value_validation(
        DISH_LEAF_NODE_DEVICE, ResultCode.OK
    )
    result = cm.is_command_allowed("AssignResources")
    logger.info(f"Command allowed result is: {result}")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["dish"]["receptor_ids"] = MKT_DISH_IDS
    json_argument = json.dumps(json_argument)

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    cm.assign_resources(
        json_argument,
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
        },
        lookahead=5,
    )


def test_assign_resources_exception_on_sn(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    """Tests assign resources exception on sn"""
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    cm.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        MagicMock(return_value=DISH_VCC_VALIDATION_RESULT_STATUS)
    )
    cm.dish_vcc_validation_status = MagicMock(
        return_value=DISH_VCC_VALIDATION_RESULT_STATUS
    )
    cm._event_cb_manager.update_k_value_validation(
        DISH_LEAF_NODE_DEVICE, ResultCode.OK
    )
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
    cm.assign_resources(
        assign_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
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

    json_decoded = json.dumps(json_argument)
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, json_decoded)

    assert result_code == [ResultCode.REJECTED]

    assert (
        "JSON validation error: Validation"
        " 'Mid TMC assign resources 2.4'" in message[0]
    )


def test_assign_resources_command_with_ok(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    cm.is_dish_vcc_config_set = True
    cm.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        MagicMock(return_value=DISH_VCC_VALIDATION_RESULT_STATUS)
    )
    cm.dish_vcc_validation_status = MagicMock(
        return_value=DISH_VCC_VALIDATION_RESULT_STATUS
    )
    cm._event_cb_manager.update_k_value_validation(
        DISH_LEAF_NODE_DEVICE, ResultCode.OK
    )
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    cm.assign_resources(
        assign_input_str,
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
        },
        lookahead=5,
    )


def test_assign_resources_command_with_mkt_ids_ok(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        MagicMock(return_value=DISH_VCC_VALIDATION_RESULT_STATUS)
    )
    cm.dish_vcc_validation_status = MagicMock(
        return_value=DISH_VCC_VALIDATION_RESULT_STATUS
    )
    cm._event_cb_manager.update_k_value_validation(
        DISH_LEAF_NODE_DEVICE, ResultCode.OK
    )
    cm.is_command_allowed("AssignResources")
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["dish"]["receptor_ids"] = MKT_DISH_IDS
    json_argument = json.dumps(json_argument)

    cm.assign_resources(
        json_argument,
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


def test_assign_resources_command_fail_subarray(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
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
    cm, _ = create_cm()
    cm.is_dish_vcc_config_set = True
    cm.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        MagicMock(return_value=DISH_VCC_VALIDATION_RESULT_STATUS)
    )
    cm.dish_vcc_validation_status = MagicMock(
        return_value=DISH_VCC_VALIDATION_RESULT_STATUS
    )
    cm._event_cb_manager.update_k_value_validation(
        DISH_LEAF_NODE_DEVICE, ResultCode.OK
    )
    cm.is_command_allowed("AssignResources")
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, " ")

    assert result_code == [ResultCode.REJECTED]
    assert message[0] == "Malformed input JSON"


def test_assign_resources_fail_check_allowed(
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
        cm.is_command_allowed("AssignResources")


def test_assign_resources_command_timeout(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
    cm, start_time = create_cm()
    cm.config.timeout_config.command_timeout = 2
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_dish_vcc_config_set = True
    cm.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        MagicMock(return_value=DISH_VCC_VALIDATION_RESULT_STATUS)
    )
    cm.dish_vcc_validation_status = MagicMock(
        return_value=DISH_VCC_VALIDATION_RESULT_STATUS
    )
    cm._event_cb_manager.update_k_value_validation(
        DISH_LEAF_NODE_DEVICE, ResultCode.OK
    )
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

    cm.assign_resources(
        assign_input_str,
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


def test_assign_resources_command_already_assigned(
    tango_context, task_callback, set_mid_sdp_csp_admin_modes
):
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
    for dev_info in cm.devices:
        if isinstance(dev_info, SubArrayDeviceInfo):
            if dev_info.dev_name == MID_SUBARRAY_DEVICE:
                dev_info.resources.append("SKA001")
                logger.info("dev_info is: %s", dev_info.resources)

    # Invoke AssignResources to assign already allocated resource - dish0001
    assign_input_str = get_assign_input_str()
    (res_code, _) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED


def check_if_subarray_is_available(cm):
    start_time = time.time()
    elapsed_time = 0
    while (cm.component.telescope_availability).get("tmc_subarrays", {}).get(
        MID_SUBARRAY_DEVICE, None
    ) is not True:
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
    cm.dish_kvalue_validation_aggregator.dln_kvalue_validation_results = (
        MagicMock(return_value=DISH_VCC_VALIDATION_RESULT_STATUS)
    )
    cm.dish_vcc_validation_status = MagicMock(
        return_value=DISH_VCC_VALIDATION_RESULT_STATUS
    )
    cm._event_cb_manager.update_k_value_validation(
        DISH_LEAF_NODE_DEVICE, ResultCode.OK
    )
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    cm.assign_resources(
        assign_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    data = task_callback.assert_call(
        status=TaskStatus.REJECTED,
        result=Anything,
        lookahead=5,
    )
    assert ResultCode.NOT_ALLOWED == data["result"][0]
    assert "AssignResources command not permitted" in data["result"][1]

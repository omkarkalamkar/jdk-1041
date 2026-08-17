import json
import threading
import time

import mock
import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_centralnode.commands.assign_resources_command_low import (
    AssignResourcesLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from ska_tmc_centralnode.utils.json_validator_decorator import (
    assign_validate_json_args,
)
from tests.settings import LOW_SUBARRAY_DEVICE, TIMEOUT, create_cm, logger


@pytest.mark.SKA_low
def test_low_assign_resources_command(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    assign_input_str = json_factory("assign_resource_low")
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
        }
    )


@pytest.mark.SKA_low
@pytest.mark.parametrize("missing_key", ["pb_id", "eb_id"])
def test_assign_resources_missing_eb_id_key_and_pb_id_key(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
    missing_key,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("assign_resource_low")
    json_argument = json.loads(assign_input_str)
    match missing_key:
        case "eb_id":
            json_argument["sdp"]["execution_block"]["eb_id"] = ""
        case "pb_id":
            json_argument["sdp"]["processing_blocks"][0]["pb_id"] = ""

    json_decoded = json.dumps(json_argument)
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, json_decoded)

    assert result_code == [ResultCode.REJECTED]

    assert missing_key in message[0]


@pytest.mark.parametrize("missing_key", ["sdp", "csp", "subarray_id", "mccs"])
def test_assign_resources_missing_sdp_csp_subarray_id_mccs_key(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
    missing_key,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument[missing_key]
    json_decoded = json.dumps(json_argument)
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, json_decoded)

    assert result_code == [ResultCode.REJECTED]
    assert missing_key in message[0]


def test_low_assign_resources_command_fail_subarray(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), str(elapsed_time)
    )

    adapter_factory = HelperAdapterFactory()

    # include exception in AssignResources command
    attrs = {"AssignResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(
        LOW_SUBARRAY_DEVICE, proxy=subarrayMock
    )
    assign_input_str = json_factory("assign_resource_low")
    assign_res_command = AssignResourcesLow(
        cm, adapter_factory=adapter_factory, logger=logger
    )
    (res_code, _) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED


def test_low_assign_resources_command_missing_subarray_beam_ids_key(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assert cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["subarray_beams"][0]["subarray_beam_id"]
    json_decoded = json.dumps(json_argument)
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, json_decoded)

    assert result_code == [ResultCode.REJECTED]
    assert "subarray_beam_id" in message[0]


@pytest.mark.SKA_low
def test_low_assign_resources_command_empty_input_json(
    tango_context, task_callback, set_low_sdp_csp_mccs_admin_modes
):
    # import debugpy; debugpy.debug_this_thread()
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, " ")

    assert result_code == [ResultCode.REJECTED]
    assert message[0] == "Malformed input JSON"


def test_low_assign_resources_command_with_invalide_key(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("invalid_key_AssignResources")
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, assign_input_str)

    assert result_code == [ResultCode.REJECTED]
    assert (
        "subarray_id key is not present in the input json argument"
        in message[0]
    )


def test_low_assign_resources_command_missing_aperture_id(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    # import debugpy; debugpy.debug_this_thread()
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assert cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["subarray_beams"][0]["apertures"][0][
        "aperture_id"
    ]
    json_decoded = json.dumps(json_argument)
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, json_decoded)

    assert result_code == [ResultCode.REJECTED]
    assert "aperture_id" in message[0]


def test_low_assign_resources_command_missing_station_ids(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    # import debugpy; debugpy.debug_this_thread()
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))

    assert cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["subarray_beams"][0]["apertures"][0][
        "station_id"
    ]
    json_decoded = json.dumps(json_argument)
    decorated = assign_validate_json_args(cm.assign_resources)

    result_code, message = decorated(cm, json_decoded)

    assert result_code == [ResultCode.REJECTED]
    assert "station_id" in message[0]


@pytest.mark.SKA_low
def test_telescope_low_assign_resources_fail_check_allowed(
    tango_context, set_low_sdp_csp_mccs_admin_modes
):
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), str(elapsed_time)
    )
    cm.config.op_state_model.perform_action("component_fault")
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("AssignResources")


def check_if_subarray_is_available(cm):
    start_time = time.time()
    elapsed_time = 0
    while (
        cm.component.telescope_availability["tmc_subarrays"][
            LOW_SUBARRAY_DEVICE
        ]
        is not True
    ):
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the SubarrayNode availability."
            )


@pytest.mark.SKA_low
def test_low_assign_resources_raises_state_model_exception(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    subarray_device.SetDirectObsState(ObsState.READY)
    check_if_subarray_is_available(cm)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("assign_resource_low")
    cm.assign_resources(
        assign_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )

    task_callback.assert_against_call(
        status=TaskStatus.REJECTED,
        result=(
            ResultCode.NOT_ALLOWED,
            "AssignResources command not permitted in observation state 4",
        ),
    )


@pytest.mark.SKA_low
def test_low_assign_resources_bad_json(
    tango_context,
    task_callback,
    set_low_sdp_csp_mccs_admin_modes,
):
    """Test assign resources with bad JSON"""
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    adapter_factory = HelperAdapterFactory()

    assign_input_str = "{ invalid json"
    assign_res_command = AssignResourcesLow(
        cm, adapter_factory=adapter_factory, logger=logger
    )
    (res_code, message) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED
    assert "Problem in loading the JSON string" in str(message)


@pytest.mark.SKA_low
def test_low_assign_resources_subarray_not_found(
    tango_context,
    task_callback,
    json_factory,
    set_low_sdp_csp_mccs_admin_modes,
):
    """Test assign resources when subarray adapter not found"""
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    adapter_factory = HelperAdapterFactory()

    assign_input_str = json_factory("assign_resource_low")
    json_arg = json.loads(assign_input_str)
    json_arg["subarray_id"] = 99
    assign_input_str = json.dumps(json_arg)

    assign_res_command = AssignResourcesLow(
        cm, adapter_factory=adapter_factory, logger=logger
    )
    assign_res_command.subarray_id = 99
    (res_code, message) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED
    assert "is not existing" in message

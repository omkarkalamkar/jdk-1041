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
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import LOW_SUBARRAY_DEVICE, TIMEOUT, create_cm, logger


@pytest.mark.SKA_lowm
def test_low_assign_resources_command(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
    assign_input_str = json_factory("command_assign_resource_low")
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
        }
    )


@pytest.mark.SKA_lowm
def test_assign_resources_missing_eb_id_key_and_processing_blocks(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("command_assign_resource_low")
    json_argument = json.loads(assign_input_str)
    json_argument["sdp"]["execution_block"]["eb_id"] = ""
    del json_argument["sdp"]["processing_blocks"]
    (res_code, _) = cm.assign_resources(json.dumps(json_argument))
    assert res_code == TaskStatus.REJECTED
    with pytest.raises(Exception) as e:
        assert "processing_blocks" in e


def test_assign_resources_missing_sdp_key(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("command_assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["sdp"]
    (res_code, message) = cm.assign_resources(json.dumps(json_argument))
    assert res_code == TaskStatus.REJECTED
    assert "sdp" in message


def test_assign_resources_missing_csp_key(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("command_assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["csp"]
    (res_code, message) = cm.assign_resources(json.dumps(json_argument))
    assert res_code == TaskStatus.REJECTED
    assert "csp" in message


def test_low_assign_resources_command_fail_subarray(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    adapter_factory = HelperAdapterFactory()

    attrs = {"fetch_skuid.return_value": 123}
    skuid = mock.Mock(**attrs)

    # include exception in AssignResources command
    attrs = {"AssignResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(
        LOW_SUBARRAY_DEVICE, proxy=subarrayMock
    )
    assign_input_str = json_factory("command_assign_resource_low")
    assign_res_command = AssignResources(
        cm, adapter_factory, skuid, logger=logger
    )
    (res_code, _) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED


def test_low_assign_resources_command_missing_subarray_beam_ids_key(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assert cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("command_assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["subarray_beams"][0]["subarray_beam_id"]
    (res_code, message) = cm.assign_resources(json.dumps(json_argument))
    assert res_code == TaskStatus.REJECTED
    assert "subarray_beam_id" in message


@pytest.mark.SKA_lowm
def test_low_assign_resources_command_empty_input_json(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    (res_code, _) = cm.assign_resources(" ")
    assert res_code == TaskStatus.REJECTED


def test_low_assign_resources_command_with_invalide_key(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("invalid_key_AssignResources")
    # json_argument = json.loads(assign_input_str)
    (res_code, message) = cm.assign_resources(
        assign_input_str, task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert (
        "subarray_id key is not present in the input json argument" in message
    )


@pytest.mark.SKA_lowm
def test_low_assign_resources_missing_subarray_id(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assign_input_str = json_factory("command_assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["subarray_id"]
    (res_code, message) = cm.assign_resources(json.dumps(json_argument))
    assert res_code == TaskStatus.REJECTED
    assert "subarray_id" in message


def test_low_assign_resources_command_missing_mccs(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assert cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("command_assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]
    res_code, message = cm.assign_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert "mccs" in message


def test_low_assign_resources_command_missing_aperture_id(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    assert cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("command_assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["subarray_beams"][0]["apertures"][0][
        "aperture_id"
    ]
    res_code, message = cm.assign_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert "aperture_id" in message


def test_low_assign_resources_command_missing_station_ids(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))

    assert cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("command_assign_resource_low")
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["subarray_beams"][0]["apertures"][0][
        "station_id"
    ]
    res_code, message = cm.assign_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert "station_id" in message


@pytest.mark.SKA_lowm
def test_telescope_low_assign_resources_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("AssignResources")


def check_if_subarray_is_available(cm):
    start_time = time.time()
    elapsed_time = 0
    while (cm.component.telescope_availability)["tmc_subarrays"][
        LOW_SUBARRAY_DEVICE
    ] is not True:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the SubarrayNode availability."
            )


@pytest.mark.SKA_lowm
def test_low_assign_resources_raises_state_model_exception(
    tango_context, task_callback, json_factory
):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    subarray_device.SetDirectObsState(ObsState.READY)
    check_if_subarray_is_available(cm)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("AssignResources")
    assign_input_str = json_factory("command_assign_resource_low")
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

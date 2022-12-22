import json
import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import create_cm, logger


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": "ska_low/tm_subarray_node/1"},
            ],
        },
        # {
        #     "class": HelperMCCSStateDevice,
        #     "devices": [
        #         {"name": "ska_low/tm_leaf_node/mccs_master"},
        #         {"name": "low-mccs/control/control"},
        #     ],
        # },
    )


def get_assign_input_str(
    assign_input_file="command_assign_resource_low.json",
):
    path = join(dirname(__file__), "..", "..", "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def get_assign_resources_command_obj():
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    adapter_factory = HelperAdapterFactory()

    attrs = {"fetch_skuid.return_value": 123}
    skuid = mock.Mock(**attrs)

    assign_res_command = AssignResources(
        cm, adapter_factory, skuid, logger=logger
    )
    return assign_res_command, adapter_factory, cm


@pytest.mark.SKA_low
def test_low_assign_resources_command(tango_context, task_callback):
    logger.info("%s", tango_context)
    _, _, cm = get_assign_resources_command_obj()
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    cm.assign_resources(json_argument, task_callback=task_callback)
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
def test_assign_resources_missing_eb_id_key_and_processing_blocks(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["sdp"]["execution_block"]["eb_id"] = ""
    del json_argument["sdp"]["processing_blocks"]
    (res_code, _) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED
    with pytest.raises(Exception) as e:
        assert "processing_blocks" in e


def test_assign_resources_missing_sdp_key(tango_context, task_callback):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["sdp"]
    (res_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED
    assert "sdp" in message


def test_low_assign_resources_command_fail_subarray(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    adapter_factory = HelperAdapterFactory()

    attrs = {"fetch_skuid.return_value": 123}
    skuid = mock.Mock(**attrs)

    # include exception in AssignResources command
    failing_dev = "ska_low/tm_subarray_node/1"
    attrs = {"AssignResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    assign_res_command = AssignResources(
        cm, adapter_factory, skuid, logger=logger
    )
    (res_code, _) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED


@pytest.mark.skip(reason="Need to run during integration of MCCS")
def test_low_assign_resources_command_missing_subarray_beam_ids_key(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    assert cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["subarray_beam_ids"]
    cm.assign_resources(json_argument, task_callback=task_callback)
    (res_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED
    assert "subarray_beam_ids" in message


@pytest.mark.SKA_low
def test_low_assign_resources_command_empty_input_json(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _, cm = get_assign_resources_command_obj()
    (res_code, _) = assign_res_command.do(" ")
    assert res_code == ResultCode.FAILED


@pytest.mark.SKA_low
def test_low_assign_resources_missing_subarray_id(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _, cm = get_assign_resources_command_obj()
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["subarray_id"]
    (res_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED
    assert "subarray_id" in message


@pytest.mark.skip(reason="Need to run during integration of MCCS")
def test_low_assign_resources_command_missing_mccs(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _, cm = get_assign_resources_command_obj()
    assert cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]
    cm.assign_resources(json_argument, task_callback=task_callback)
    (res_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED
    assert "mccs" in message


@pytest.mark.skip(reason="Need to run during integration of MCCS")
def test_low_assign_resources_command_missing_channel_blocks(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _, cm = get_assign_resources_command_obj()
    assert cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["channel_blocks"]
    cm.assign_resources(json_argument, task_callback=task_callback)
    (res_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED
    assert "channel_blocks" in message


@pytest.mark.skip(reason="Need to run during integration of MCCS")
def test_low_assign_resources_command_missing_station_ids(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _, cm = get_assign_resources_command_obj()

    assert cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["station_ids"]
    cm.assign_resources(json_argument, task_callback=task_callback)
    (res_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED
    assert "station_ids" in message


@pytest.mark.SKA_low
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

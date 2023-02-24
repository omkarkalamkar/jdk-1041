import json
import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.device_info import SubArrayDeviceInfo
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    create_cm,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
            ],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": MID_SDP_MLN_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    path = join(dirname(__file__), "..", "..", "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def get_assign_resources_command_obj():
    cm, start_time = create_cm()
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


def test_assign_resources_command_queued(tango_context, task_callback):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    cm.assign_resources(json.dumps(json_argument), task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )


def test_assign_resources_command_missing_eb_id_key_and_processing_blocks(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["sdp"]["execution_block"]["eb_id"]
    del json_argument["sdp"]["processing_blocks"]
    with pytest.raises(ValueError):
        cm.assign_resources(
            json.dumps(json_argument), task_callback=task_callback
        )


def test_assign_resources_command_with_ok(tango_context, task_callback):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    cm.assign_resources(json.dumps(json_argument), task_callback=task_callback)
    (res_code, _) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.OK


def test_assign_resources_command_missing_sdp_key(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["sdp"]
    (res_code, message) = cm.assign_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert "sdp" in message


def test_assign_resources_command_fail_subarray(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
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
        MID_SUBARRAY_DEVICE, proxy=subarrayMock
    )

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    assign_res_command = AssignResources(
        cm, adapter_factory, skuid, logger=logger
    )
    assign_res_command.assign_resources(
        json_argument, logger=logger, task_callback=task_callback
    )
    (res_code, _) = assign_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED


def test_telescope_assign_resources_command_empty_input_json(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    cm.is_command_allowed("AssignResources")
    cm.assign_resources("", task_callback=task_callback)
    (res_code, _) = assign_res_command.do(" ")
    assert res_code == ResultCode.FAILED


def test_assign_resources_command_missing_subarray_id(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["subarray_id"]
    (res_code, message) = cm.assign_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert "subarray_id" in message


def test_assign_resources_command_missing_dish(tango_context, task_callback):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["dish"]
    (res_code, message) = cm.assign_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert "dish" in message


def test_assign_resources_command_missing_receptor_ids(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    assign_res_command, _, cm = get_assign_resources_command_obj()
    cm.is_command_allowed("AssignResources")
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["dish"]["receptor_ids"]
    (res_code, message) = cm.assign_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert "receptor_ids" in message


def test_assign_resources_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("AssignResources")


def test_assign_resources_command_already_assigned(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    adapter_factory = HelperAdapterFactory()

    attrs = {"fetch_skuid.return_value": 123}
    skuid = mock.Mock(**attrs)

    assign_res_command = AssignResources(
        cm, adapter_factory, skuid, logger=logger
    )
    # dish0001 is assigned to Subarray1
    for devInfo in cm.devices:
        if isinstance(devInfo, SubArrayDeviceInfo):
            if devInfo.dev_name == MID_SUBARRAY_DEVICE:
                devInfo.resources.append("dish0001")
                logger.info("devInfo is: %s", devInfo.resources)

    # Invoke AssignResources to assign already allocated resource - dish0001
    assign_input_str = get_assign_input_str()
    cm.assign_resources(assign_input_str, task_callback=task_callback)
    (res_code, message) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED
    assert "dish0001" in message


def test_mid_assign_resources_command_with_invalid_key(
    tango_context, task_callback, json_factory
):
    logger.info("%s", tango_context)
    _, _, cm = get_assign_resources_command_obj()
    assign_input_str = json_factory("invalid_key_AssignResources")
    (res_code, message) = cm.assign_resources(
        assign_input_str, task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert (
        "subarray_id key is not present in the input json argument" in message
    )

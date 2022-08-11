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
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)
from tango import DevState

from ska_tmc_centralnode.commands.release_resources_command import (
    ReleaseResources,
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
        {
            "class": HelperMCCSStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
                {"name": "low-mccs/control/control"},
            ],
        },
    )


def get_release_input_str(
    release_input_file="command_mccs_ReleaseResources.json",
):
    path = join(
        dirname(__file__), "..", "..", "..", "data", release_input_file
    )
    with open(path, "r") as f:
        release_input_str = f.read()
    return release_input_str


def get_release_resources_command_obj():
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()
    release_command = ReleaseResources(cm, my_adapter_factory, logger=logger)
    return release_command, my_adapter_factory, cm


def test_low_release_resources_command_queued(tango_context, task_callback):
    _, _, cm = get_release_resources_command_obj()
    cm.is_command_allowed("ReleaseResources")
    release_input_str = get_release_input_str()
    json_argument = json.loads(release_input_str)
    cm.release_resources(json_argument, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )


def test_low_release_resources_command_with_ok(tango_context, task_callback):
    release_res_command, _, cm = get_release_resources_command_obj()
    cm.is_command_allowed("ReleaseResources")
    release_input_str = get_release_input_str()
    json_argument = json.loads(release_input_str)
    cm.release_resources(json_argument, task_callback=task_callback)
    (res_code, _) = release_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.OK


def test_low_release_resources_command_fail_subarray(
    tango_context, task_callback
):
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    adapter_factory = HelperAdapterFactory()

    # include exception in ReleaseResources command
    failing_dev = "ska_low/tm_subarray_node/1"
    attrs = {"ReleasAlleResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)
    release_input_str = get_release_input_str()
    json_argument = json.loads(release_input_str)
    release_res_command = ReleaseResources(cm, adapter_factory, logger=logger)
    release_res_command.release_resources(
        json_argument, logger=logger, task_callback=task_callback
    )
    (res_code, _) = release_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED


def test_low_release_resources_command_empty_input_json(
    tango_context, task_callback
):
    release_res_command, _, cm = get_release_resources_command_obj()
    cm.is_command_allowed("ReleaseResources")
    cm.release_resources("", task_callback=task_callback)
    (res_code, _) = release_res_command.do(" ")
    assert res_code == ResultCode.FAILED


def test_low_release_resources_command_missing_subarray_id(
    tango_context, task_callback
):
    release_res_command, _, cm = get_release_resources_command_obj()
    cm.is_command_allowed("ReleaseResources")
    release_input_str = get_release_input_str()
    json_argument = json.loads(release_input_str)
    del json_argument["subarray_id"]
    cm.release_resources(json_argument, task_callback=task_callback)
    (res_code, message) = release_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED
    assert "subarray_id" in message


def test_low_release_resources_fail_check_allowed(tango_context):
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("ReleaseResources")

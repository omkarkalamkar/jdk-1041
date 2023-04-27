import json
import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import DevState

from ska_tmc_centralnode.commands.release_resources_command import (
    ReleaseResources,
)
from ska_tmc_centralnode.model.input import InputParameterMid
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
                {
                    "name": MID_CSP_MLN_DEVICE,
                },
                {"name": MID_SDP_MLN_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def get_release_input_str(release_input_file="command_ReleaseResources.json"):
    path = join(
        dirname(__file__), "..", "..", "..", "data", release_input_file
    )
    with open(path, "r") as f:
        release_input_str = f.read()
    return release_input_str


def get_release_resources_command_obj():
    cm, start_time = create_cm(_input_parameter=InputParameterMid(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    my_adapter_factory = HelperAdapterFactory()
    release_command = ReleaseResources(cm, my_adapter_factory, logger=logger)
    return release_command, my_adapter_factory, cm


def test_mid_release_resources_command(tango_context, task_callback):
    _, _, cm = get_release_resources_command_obj()
    cm.is_command_allowed("ReleaseResources")
    release_input_str = get_release_input_str()
    json_argument = json.loads(release_input_str)
    cm.release_resources(json_argument, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )


def test_mid_release_resources_command_with_ok(tango_context, task_callback):
    release_res_command, _, cm = get_release_resources_command_obj()
    cm.is_command_allowed("ReleaseResources")
    release_input_str = get_release_input_str()
    json_argument = json.loads(release_input_str)
    cm.release_resources(json_argument, task_callback=task_callback)
    (res_code, _) = release_res_command.do(json_argument)
    assert res_code == ResultCode.OK


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
    json_argument = json.loads(release_input_str)
    release_res_command = ReleaseResources(cm, adapter_factory, logger=logger)
    cm.release_resources(json_argument, task_callback=task_callback)
    (res_code, _) = release_res_command.do(json.dumps(json_argument))
    assert res_code == ResultCode.FAILED


def test_mid_release_resources_command_empty_input_json(
    tango_context, task_callback
):
    release_res_command, _, cm = get_release_resources_command_obj()
    cm.is_command_allowed("ReleaseResources")
    cm.release_resources("", task_callback=task_callback)
    (res_code, _) = release_res_command.do("")
    assert res_code == ResultCode.FAILED


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
    release_res_command, _, cm = get_release_resources_command_obj()
    release_input_str = json_factory("invalid_key_ReleaseResources")
    # with pytest.raises(InvalidJSONError):
    cm.release_resources(release_input_str, task_callback=task_callback)
    (res_code, _) = release_res_command.do("")
    assert res_code == ResultCode.FAILED

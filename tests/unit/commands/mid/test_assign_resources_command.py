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
from tests.mock_callable import MockCallable
from tests.settings import create_cm, logger


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [{"name": "ska_mid/tm_subarray_node/1"}],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    path = join(dirname(__file__), "..", "..", "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def test_telescope_assign_resources_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    unique_id = f"{time.time()}_TelescopeOn"
    task_callback = MockCallable(unique_id)
    cm.is_command_allowed("AssignResources")
    cm.assign_resources(task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED


def test_telescope_assign_resources_command_missing_eb_id_key(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    adapter_factory = HelperAdapterFactory()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["sdp"]["eb_id"] = ""

    assign_rescources_command = AssignResources(
        cm, adapter_factory, logger=logger
    )
    (result_code, _) = assign_rescources_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED


def test_telescope_assign_resources_command_missing_sdp_key(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    adapter_factory = HelperAdapterFactory()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["sdp"]
    assign_rescources_command = AssignResources(
        cm, adapter_factory, logger=logger
    )
    (result_code, message) = assign_rescources_command.do(
        json.dumps(json_argument)
    )
    assert result_code == ResultCode.FAILED
    assert "sdp" in message


def test_telescope_assign_resources_command_fail_subarray(tango_context):
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
    failing_dev = "ska_mid/tm_subarray_node/1"
    attrs = {"AssignResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)

    unique_id = f"{time.time()}_AssignResources"
    task_callback = MockCallable(unique_id)

    assign_res_command = AssignResources(
        cm, adapter_factory, skuid, logger=logger
    )
    assign_res_command.assign_resources(
        logger=logger, task_callback=task_callback
    )
    assert task_callback.status == TaskStatus.FAILED


def test_telescope_assign_resources_command_empty_input_json(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    adapter_factory = HelperAdapterFactory()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["sdp"]
    assign_rescources_command = AssignResources(
        cm, adapter_factory, logger=logger
    )
    (result_code, _) = assign_rescources_command.do(" ")
    assert result_code == ResultCode.FAILED


def test_telescope_assign_resources_command_missing_subarray_id(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    adapter_factory = HelperAdapterFactory()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["subarray_id"]
    assign_rescources_command = AssignResources(
        cm, adapter_factory, logger=logger
    )
    (result_code, message) = assign_rescources_command.do(
        json.dumps(json_argument)
    )
    assert result_code == ResultCode.FAILED
    assert "subarray_id" in message


def test_telescope_assign_resources_command_missing_dish(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    adapter_factory = HelperAdapterFactory()
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["dish"]
    assign_rescources_command = AssignResources(
        cm, adapter_factory, logger=logger
    )
    (result_code, message) = assign_rescources_command.do(
        json.dumps(json_argument)
    )
    assert result_code == ResultCode.FAILED
    assert "dish" in message


def test_telescope_assign_resources_command_missing_receptor_ids(
    tango_context,
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    adapter_factory = HelperAdapterFactory()
    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["dish"]["receptor_ids"]
    assign_rescources_command = AssignResources(
        cm, adapter_factory, logger=logger
    )
    (result_code, message) = assign_rescources_command.do(
        json.dumps(json_argument)
    )
    assert result_code == ResultCode.FAILED
    assert "receptor_ids" in message


def test_telescope_assign_resources_fail_check_allowed(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("TelescopeOn")


def test_telescope_assign_resources_command_already_assigned(tango_context):
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
    subarray = "ska_mid/tm_subarray_node/1"
    for devInfo in cm.devices:
        if isinstance(devInfo, SubArrayDeviceInfo):
            if devInfo.dev_name == subarray:
                devInfo.resources.append("dish0001")
                logger.info("devInfo is: %s", devInfo.resources)

    # Invoke AssignResources to assign already allocated resource - dish0001
    assign_input_str = get_assign_input_str()
    (result_code, message) = assign_res_command.do(assign_input_str)
    assert result_code == ResultCode.FAILED
    assert "dish0001" in message

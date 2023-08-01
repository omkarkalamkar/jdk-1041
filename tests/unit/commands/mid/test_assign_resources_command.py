import json
import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DevFactory, FaultType
from ska_tmc_common.device_info import SubArrayDeviceInfo
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_base_device import HelperBaseDevice
from ska_tmc_common.test_helpers.helper_dish_device import HelperDishDevice
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
    TIMEOUT,
    create_cm,
    logger,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
            ],
        },
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_SDP_MLN_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
        {
            "class": HelperDishDevice,
            "devices": [
                {"name": DISH_MASTER_DEVICE},
            ],
        },
    )


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    path = join(dirname(__file__), "..", "..", "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def test_assign_resources_command_completed(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
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
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK},
        lookahead=5,
    )


def test_assign_resources_command_with_mkt_ids_completed(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
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
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK},
        lookahead=5,
    )


def test_assign_resources_exception_on_sn(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.is_command_allowed("AssignResources")
    defect = {
        "enabled": True,
        "fault_type": FaultType.COMMAND_NOT_ALLOWED,
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
    result = task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
    )
    assert "Command not allowed on leaf node." in result["exception"]
    subarray_device.SetDefective(json.dumps({"enabled": False}))


def test_assign_resources_command_missing_eb_id_key_and_processing_blocks(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    cm, _ = create_cm()

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

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
        "JSON validation error: data is not compliant with https://schema.skao.int/ska-tmc-assignresources/2.1"
        in message
    )
    assert res_code == TaskStatus.REJECTED


def test_assign_resources_command_with_ok(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm, _ = create_cm()
    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(MID_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)
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
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK},
        lookahead=5,
    )


def test_assign_resources_command_with_mkt_ids_ok(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    cm, _ = create_cm()
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
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )


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
    assign_res_command = AssignResources(
        cm, adapter_factory, skuid, logger=logger
    )
    assign_res_command.assign_resources(
        json.loads(assign_input_str),
        logger=logger,
        task_callback=task_callback,
    )
    (res_code, _) = assign_res_command.do(assign_input_str)
    assert res_code == ResultCode.FAILED


def test_telescope_assign_resources_command_empty_input_json(
    tango_context, task_callback
):
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_command_allowed("AssignResources")
    cm.assign_resources("", task_callback=task_callback)
    (res_code, _) = cm.assign_resources(" ")
    assert res_code == TaskStatus.REJECTED


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


def test_assign_resources_command_timeout(tango_context, task_callback):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    cm.command_timeout = 2
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
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

    cm.assign_resources(assign_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED,
        result=ResultCode.FAILED,
        exception="Timeout has occured, command failed",
    )
    subarray_device.SetDefective(json.dumps({"enabled": False}))


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
    # SKA001 is assigned to Subarray1
    for devInfo in cm.devices:
        if isinstance(devInfo, SubArrayDeviceInfo):
            if devInfo.dev_name == MID_SUBARRAY_DEVICE:
                devInfo.resources.append("SKA001")
                logger.info("devInfo is: %s", devInfo.resources)

    # Invoke AssignResources to assign already allocated resource - dish0001
    assign_input_str = get_assign_input_str()
    cm.assign_resources(assign_input_str, task_callback=task_callback)
    (res_code, message) = assign_res_command.do(assign_input_str)
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

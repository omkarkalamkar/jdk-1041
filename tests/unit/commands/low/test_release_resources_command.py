import json
import time

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_base_device import HelperBaseDevice
from tango import DevState

from ska_tmc_centralnode.commands.release_resources_command import (
    ReleaseResources,
)
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
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
                {"name": LOW_SUBARRAY_DEVICE},
            ],
        },
        # {
        #     "class": HelperMCCSStateDevice,
        #     "devices": [
        #         {"name": "ska_low/tm_leaf_node/mccs_master"},
        #         {"name": "low-mccs/control/control"},
        #     ],
        # },
        {
            "class": HelperBaseDevice,
            "devices": [
                {
                    "name": LOW_CSP_MLN_DEVICE,
                },
                {"name": LOW_SDP_MLN_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def get_release_resources_command_obj():
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    helper_adapter_factory = HelperAdapterFactory()
    release_command = ReleaseResources(
        cm, helper_adapter_factory, logger=logger
    )
    return release_command, helper_adapter_factory, cm


@pytest.mark.SKA_low
def test_low_release_resources_command(
    tango_context, task_callback, json_factory
):
    _, _, cm = get_release_resources_command_obj()
    cm.is_command_allowed("ReleaseResources")

    dev_factory = DevFactory()
    subarray_device = dev_factory.get_device(LOW_SUBARRAY_DEVICE)
    subarray_device.SetisSubarrayAvailable(True)
    check_if_subarray_is_available(cm)

    release_input_str = json_factory("command_release_resource_low")
    cm.release_resources(release_input_str, task_callback=task_callback)
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
def test_low_release_resources_command_fail_subarray(
    tango_context,
    task_callback,
    json_factory,
):
    cm, start_time = create_cm(_input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    adapter_factory = HelperAdapterFactory()

    # include exception in ReleaseResources command
    attrs = {"ReleaseAllResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    adapter_factory.get_or_create_adapter(
        LOW_SUBARRAY_DEVICE, proxy=subarrayMock
    )
    release_input_str = json_factory("command_release_resource_low")
    assign_res_command = ReleaseResources(cm, adapter_factory, logger=logger)
    (res_code, _) = assign_res_command.do(release_input_str)
    assert res_code == ResultCode.FAILED


@pytest.mark.SKA_low
def test_low_release_resources_empty_input_json(tango_context, task_callback):
    release_res_command, _, cm = get_release_resources_command_obj()
    cm.release_resources("", task_callback=task_callback)
    (res_code, _) = cm.release_resources(" ")
    assert res_code == TaskStatus.REJECTED


@pytest.mark.SKA_low
def test_low_release_resources_command_with_invalide_key(
    tango_context, task_callback, json_factory
):
    _, _, cm = get_release_resources_command_obj()
    release_input_str = json_factory("invalid_key_ReleaseResources")
    (res_code, message) = cm.release_resources(
        release_input_str, task_callback=task_callback
    )
    assert res_code == TaskStatus.REJECTED
    assert (
        "subarray_id key is not present in the input json argument" in message
    )


@pytest.mark.SKA_low
def test_low_release_resources_missing_subarray_id(
    tango_context, task_callback, json_factory
):
    release_res_command, _, cm = get_release_resources_command_obj()
    release_input_str = json_factory("command_release_resource_low")
    json_argument = json.loads(release_input_str)
    del json_argument["subarray_id"]
    cm.release_resources(
        json.dumps(json_argument), task_callback=task_callback
    )
    (res_code, message) = cm.release_resources(json.dumps(json_argument))
    assert res_code == TaskStatus.REJECTED
    assert "subarray_id" in message


@pytest.mark.SKA_low
def test_low_release_resources_fail_check_allowed(tango_context):
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("ReleaseResources")


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

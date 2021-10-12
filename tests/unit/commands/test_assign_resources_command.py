import json
import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.obs.obs_device import SKAObsDevice
from test_cm_all_working import create_cm

from ska_tmc_centralnode_mid.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode_mid.manager.adapters import (
    DishAdapter,
    SubArrayAdapter,
)
from tests.helper_adapter_factory import HelperAdapterFactory
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import count_faulty_devices, logger


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [{"name": "ska_mid/tm_subarray_node/1"}],
        },
        {
            "class": SKAObsDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    path = join(dirname(__file__), "..", "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    return assign_input_str


def get_assign_resources_command_obj():
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    my_adapter_factory = HelperAdapterFactory()

    attrs = {"fetch_skuid.return_value": 123}
    skuid = mock.Mock(**attrs)

    assign_res_command = AssignResources(
        cm, cm.op_state_model, my_adapter_factory, skuid
    )
    return assign_res_command, my_adapter_factory


def test_telescope_assign_resources_command(tango_context):
    logger.info("%s", tango_context)
    assign_res_command, my_adapter_factory = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    (result_code, _) = assign_res_command.do(assign_input_str)
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.AssignResources.assert_called()


def test_telescope_assign_resources_command_missing_eb_id_key(tango_context):
    logger.info("%s", tango_context)
    assign_res_command, my_adapter_factory = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["sdp"]["eb_id"] = ""
    (result_code, _) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.AssignResources.assert_called()


def test_telescope_assign_resources_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    my_adapter_factory = HelperAdapterFactory()

    attrs = {"fetch_skuid.return_value": 123}
    skuid = mock.Mock(**attrs)

    # include exception in AssignResources command
    failing_dev = "ska_mid/tm_subarray_node/1"
    attrs = {"AssignResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)

    assign_res_command = AssignResources(
        cm, cm.op_state_model, my_adapter_factory, skuid
    )
    assign_input_str = get_assign_input_str()
    (result_code, message) = assign_res_command.do(assign_input_str)
    assert result_code == ResultCode.FAILED
    assert failing_dev in message


def test_telescope_assign_resources_command_empty_input_json(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    (result_code, _) = assign_res_command.do("")
    assert result_code == ResultCode.FAILED


def test_telescope_assign_resources_command_missing_sdp_key(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["sdp"]
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "sdp" in message


def test_telescope_assign_resources_command_missing_transaction_id(
    tango_context,
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["transaction_id"]
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "transaction_id" in message


def test_telescope_assign_resources_command_missing_subarray_id(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["subarray_id"]
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "subarray_id" in message


def test_telescope_assign_resources_command_missing_dish(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["dish"]
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "dish" in message


def test_telescope_assign_resources_command_missing_receptor_ids(
    tango_context,
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["dish"]["receptor_ids"]
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "receptor_ids" in message


def test_telescope_assign_resources_fail_check_allowed(tango_context):

    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()
    cm.input_parameter.tm_dish_dev_names = []
    assign_res_command = AssignResources(
        cm, cm.op_state_model, my_adapter_factory
    )
    with pytest.raises(Exception):
        assign_res_command.check_allowed()

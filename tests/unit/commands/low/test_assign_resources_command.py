import json
import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import SubArrayAdapter
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode.model.input import InputParameterLow

# from ska_tmc_common.test_helpers.helper_subarray_device import (
#     HelperSubArrayDevice,
# )
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


def get_assign_input_str(
    assign_input_file="command_mccs_AssignResources.json",
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

    my_adapter_factory = HelperAdapterFactory()

    attrs = {"fetch_skuid.return_value": 123}
    skuid = mock.Mock(**attrs)

    assign_res_command = AssignResources(
        cm, cm.op_state_model, my_adapter_factory, skuid
    )
    return assign_res_command, my_adapter_factory

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_command(tango_context):
    logger.info("%s", tango_context)
    assign_res_command, my_adapter_factory = get_assign_resources_command_obj()
    assign_input_str = get_assign_input_str()
    assert assign_res_command.check_allowed()
    (result_code, _) = assign_res_command.do(assign_input_str)
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.AssignResources.assert_called()

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )

    my_adapter_factory = HelperAdapterFactory()

    attrs = {"fetch_skuid.return_value": 123}
    skuid = mock.Mock(**attrs)

    # include exception in AssignResources command
    failing_dev = "ska_low/tm_subarray_node/1"
    attrs = {"AssignResources.side_effect": Exception}
    subarrayMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)

    assign_res_command = AssignResources(
        cm, cm.op_state_model, my_adapter_factory, skuid
    )
    assign_input_str = get_assign_input_str()
    assert assign_res_command.check_allowed()
    (result_code, message) = assign_res_command.do(assign_input_str)
    assert result_code == ResultCode.FAILED
    assert failing_dev in message

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_command_missing_subarray_beam_ids_key(
    tango_context,
):
    logger.info("%s", tango_context)
    assign_res_command, my_adapter_factory = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    json_argument["mccs"]["subarray_beam_ids"] = ""
    assert assign_res_command.check_allowed()
    (result_code, _) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.AssignResources.assert_called()

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_command_empty_input_json(
    tango_context,
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()
    assert assign_res_command.check_allowed()
    (result_code, _) = assign_res_command.do("")
    assert result_code == ResultCode.FAILED

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_command_missing_subarray_id(
    tango_context,
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["subarray_id"]
    assert assign_res_command.check_allowed()
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "subarray_id" in message

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_command_missing_mccs(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]
    assert assign_res_command.check_allowed()
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "mccs" in message

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_command_missing_channel_blocks(
    tango_context,
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["channel_blocks"]
    assert assign_res_command.check_allowed()
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "channel_blocks" in message

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_command_missing_station_ids(
    tango_context,
):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    assign_res_command, _ = get_assign_resources_command_obj()

    assign_input_str = get_assign_input_str()
    json_argument = json.loads(assign_input_str)
    del json_argument["mccs"]["station_ids"]
    assert assign_res_command.check_allowed()
    (result_code, message) = assign_res_command.do(json.dumps(json_argument))
    assert result_code == ResultCode.FAILED
    assert "station_ids" in message

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_low_assign_resources_fail_check_allowed(tango_context):

    logger.info("%s", tango_context)
    cm, start_time = create_cm(input_parameter=InputParameterLow(None))
    elapsed_time = time.time() - start_time
    logger.info(
        "checked %s devices in %s", len(cm.checked_devices), elapsed_time
    )
    my_adapter_factory = HelperAdapterFactory()
    cm.input_parameter.mccs_master_leaf_node = []
    assign_res_command = AssignResources(
        cm, cm.op_state_model, my_adapter_factory
    )
    with pytest.raises(CommandNotAllowed):
        assign_res_command.check_allowed()

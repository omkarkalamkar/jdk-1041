import time
from os.path import dirname, join

import mock
import pytest
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode_mid.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode_mid.manager.adapters import SubArrayAdapter
from ska_tmc_centralnode_mid.model.input import InputParameterLow
from tests.helper_adapter_factory import HelperAdapterFactory
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
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
            "class": HelperStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
                {"name": "low-mccs/control/control"},
            ],
        },
    )


def get_assign_input_str(assign_input_file="command_AssignResources.json"):
    path = join(
        dirname(__file__), "..", "..", "data", "low", assign_input_file
    )
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


def test_telescope_assign_resources_command(tango_context):
    logger.info("%s", tango_context)
    assign_res_command, my_adapter_factory = get_assign_resources_command_obj()
    assign_input_str = get_assign_input_str()
    assert assign_res_command.check_allowed()
    (result_code, _) = assign_res_command.do(assign_input_str)
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.AssignResources.assert_called()

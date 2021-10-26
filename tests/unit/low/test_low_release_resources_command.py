import time
from os.path import dirname, join

import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.obs.obs_device import SKAObsDevice

from ska_tmc_centralnode_mid.commands.release_resources_command import (
    ReleaseResources,
)
from ska_tmc_centralnode_mid.manager.adapters import SubArrayAdapter
from ska_tmc_centralnode_mid.model.input import InputParameterLow
from tests.helper_adapter_factory import HelperAdapterFactory
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
            "class": SKAObsDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
                {"name": "low-mccs/control/control"},
            ],
        },
    )


def get_release_input_str(release_input_file="command_ReleaseResources.json"):
    path = join(
        dirname(__file__), "..", "..", "data", "low", release_input_file
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

    release_command = ReleaseResources(
        cm, cm.op_state_model, my_adapter_factory
    )
    return release_command, my_adapter_factory


def test_telescope_release_resources_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    release_command, my_adapter_factory = get_release_resources_command_obj()

    release_input_str = get_release_input_str()
    assert release_command.check_allowed()
    (result_code, _) = release_command.do(release_input_str)
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.ReleaseResources.assert_called()

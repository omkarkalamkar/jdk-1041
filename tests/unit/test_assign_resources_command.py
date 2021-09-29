
import time
import pytest
import mock
from os.path import dirname, join
from ska_tmc_centralnode_mid.manager.adapters import DishAdapter, SubArrayAdapter
from tests.helper_adapter_factory import HelperAdapterFactory
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.commands.assign_resources_command import AssignResources
from tests.settings import  logger
from tests.helper_subarray_device import HelperSubArrayDevice
from ska_tango_base.obs.obs_device import SKAObsDevice
from test_cm_all_working import create_cm
from tests.settings import logger, count_faulty_devices

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_subarray_node/1"
                },
                {
                    "name": "ska_mid/tm_subarray_node/2"
                },
                {
                    "name": "ska_mid/tm_subarray_node/3"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray02"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray03"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray02"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray03"
                }
            ],
        },
        {
            "class": SKAObsDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_leaf_node/csp_master"
                },
                {
                    "name": "mid_csp/elt/master"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_master"
                },
                {
                    "name": "mid_sdp/elt/master"
                },
                {
                    "name": "mid_d0001/elt/master"
                }
            ]
        }
    )

def test_telescope_assign_resources_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)

    my_adapter_factory = HelperAdapterFactory()

    attrs = {'fetch_skuid.return_value': 123}
    skuid = mock.Mock(**attrs)
    on_command = AssignResources(cm, cm.op_state_model, my_adapter_factory, skuid)
    assign_input_file = "command_AssignResources.json"
    path = join(dirname(__file__), "..", "data", assign_input_file)
    with open(path, "r") as f:
        assign_input_str = f.read()
    (result_code, _) = on_command.do(assign_input_str)
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.AssignResources.assert_called()
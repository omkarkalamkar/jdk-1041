
import time
import pytest
from ska_tmc_centralnode_mid.manager.adapters import BaseAdapter, CspMaster, Dish
from tests.helper_adapter_factory import HelperAdapterFactory
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.commands.stow_antennas_command import StowAntennas
from tests.settings import  logger
from tests.helper_subarray_device import HelperSubArrayDevice
from ska_tango_base.obs.obs_device import SKAObsDevice
from test_cm_all_working import create_cm
from tests.settings import DEVICE_LIST, SLEEP_TIME, TIMEOUT, logger, count_faulty_devices

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

def test_telescope_stow_antennas_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)

    my_adapter_factory = HelperAdapterFactory()
    on_command = StowAntennas(cm, cm.op_state_model, my_adapter_factory)
    (result_code, _) = on_command.do(["1"])
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, Dish):
            adapter.proxy.SetStowMode.assert_called()

import time
import pytest
from ska_tmc_centralnode_mid.manager.adapters import BaseAdapter, SubArrayAdapter, DishAdapter
from tests.helper_adapter_factory import HelperAdapterFactory
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.commands.telescope_off_command import TelescopeOff
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
                    "name": "ska_mid/tm_leaf_node/sdp_master"
                },
                {
                    "name": "mid_d0001/elt/master"
                }
            ]
        }
    )

def test_telescope_off_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    # num_faulty = count_faulty_devices(cm)
    # assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)

    my_adapter_factory = HelperAdapterFactory()
    on_command = TelescopeOff(cm, cm.op_state_model, my_adapter_factory)
    (result_code, _) = on_command.do()
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, DishAdapter):
            adapter.proxy.SetStandbyFPMode.assert_called() 
            adapter.proxy.SetStandbyLPMode.assert_called()
            continue
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.TelescopeOff.assert_called() 
            continue
        
        adapter.proxy.TelescopeOff.assert_called() 
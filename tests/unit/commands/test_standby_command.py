
import time
import pytest
import mock
from ska_tmc_centralnode_mid.manager.adapters import BaseAdapter, SubArrayAdapter, DishAdapter
from tests.helper_adapter_factory import HelperAdapterFactory
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.commands.telescope_standby_command import TelescopeStandby
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

def test_telescope_standby_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    # num_faulty = count_faulty_devices(cm)
    # assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)

    my_adapter_factory = HelperAdapterFactory()
    standby_command = TelescopeStandby(cm, cm.op_state_model, my_adapter_factory)
    (result_code, _) = standby_command.do()
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, DishAdapter):
            adapter.proxy.SetStandbyFPMode.assert_called() 
            adapter.proxy.SetStandbyLPMode.assert_called()
            continue
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.TelescopeStandBy.assert_called() 
            continue
        
        adapter.proxy.TelescopeStandBy.assert_called() 

def test_telescope_standby_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "ska_mid/tm_subarray_node/1"

    attrs = {'TelescopeStandBy.side_effect': Exception}
    subarrayMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)

    standby_command = TelescopeStandby(cm, cm.op_state_model, my_adapter_factory)
    (result_code, message) = standby_command.do()
    assert result_code == ResultCode.FAILED
    assert failing_dev in message

def test_telescope_standby_command_fail_dish(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)
    my_adapter_factory = HelperAdapterFactory()

    # include exception in TelescopeStandby command
    failing_dev = "mid_d0001/elt/master"

    attrs = {'SetStandbyFPMode.side_effect': Exception}
    dishMasterLeafMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(failing_dev, proxy=dishMasterLeafMock)

    standby_command = TelescopeStandby(cm, cm.op_state_model, my_adapter_factory)
    (result_code, message) = standby_command.do()
    assert result_code == ResultCode.FAILED
    assert failing_dev in message

def test_telescope_standby_fail_check_allowed(tango_context):

    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)
    my_adapter_factory = HelperAdapterFactory()
    cm.input_parameter.tm_dish_dev_names = []
    standby_command = TelescopeStandby(cm, cm.op_state_model, my_adapter_factory)
    with pytest.raises(Exception):
        standby_command.check_allowed()
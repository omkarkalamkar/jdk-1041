
import time
import pytest
import mock
from os.path import dirname, join
from ska_tmc_centralnode_mid.manager.adapters import DishAdapter, SubArrayAdapter
from tests.helper_adapter_factory import HelperAdapterFactory
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.commands.release_resources_command import ReleaseResources
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

def get_release_input_str(release_input_file = "command_ReleaseResources.json"):
    path = join(dirname(__file__), "..", "..", "data", release_input_file)
    with open(path, "r") as f:
        release_input_str = f.read()
    return release_input_str

def test_telescope_release_resources_command(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)

    my_adapter_factory = HelperAdapterFactory()

    release_command = ReleaseResources(cm, cm.op_state_model, my_adapter_factory)
    release_input_str = get_release_input_str()
    (result_code, _) = release_command.do(release_input_str)
    assert result_code == ResultCode.OK
    for adapter in my_adapter_factory.adapters:
        if isinstance(adapter, SubArrayAdapter):
            adapter.proxy.ReleaseAllResources.assert_called()

def test_telescope_release_resources_command_fail_subarray(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)
    
    my_adapter_factory = HelperAdapterFactory()

    # include exception in ReleaseResources command
    failing_dev = "ska_mid/tm_subarray_node/1"
    attrs = {'ReleaseAllResources.side_effect': Exception}
    subarrayMock = mock.Mock(**attrs)
    my_adapter_factory.get_or_create_adapter(failing_dev, proxy=subarrayMock)

    release_command = ReleaseResources(cm, cm.op_state_model, my_adapter_factory)
    release_input_str = get_release_input_str()
    (result_code, message) = release_command.do(release_input_str)
    assert result_code == ResultCode.FAILED
    assert failing_dev in message

def test_telescope_release_resources_command_empty_input_json(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)

    my_adapter_factory = HelperAdapterFactory()

    release_command = ReleaseResources(cm, cm.op_state_model, my_adapter_factory)
    (result_code, _) = release_command.do("")
    assert result_code == ResultCode.FAILED

def test_telescope_release_resources_command_missing_transaction_id(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)
    
    my_adapter_factory = HelperAdapterFactory()

    release_command = ReleaseResources(cm, cm.op_state_model, my_adapter_factory)
    
    (result_code, message) = release_command.do('{"interface":"https://schema.skao.int/ska-tmc-releaseresources/2.0","subarray_id":1,"release_all":true,"receptor_ids":[]}')

    assert result_code == ResultCode.FAILED
    assert "transaction_id" in message

def test_telescope_release_resources_command_missing_subarray_id(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)
    
    my_adapter_factory = HelperAdapterFactory()

    release_command = ReleaseResources(cm, cm.op_state_model, my_adapter_factory)
    # release_input_str = get_release_input_str("missing_transaction_id_ReleaseResources.json")
    (result_code, message) = release_command.do('{"interface":"https://schema.skao.int/ska-tmc-releaseresources/2.0","transaction_id":"txn-....-00001","release_all":true,"receptor_ids":[]}')

    assert result_code == ResultCode.FAILED
    assert "subarray_id" in message

def test_telescope_release_resources_fail_check_allowed(tango_context):

    logger.info("%s", tango_context)
    cm, start_time = create_cm()
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", len(cm.checked_devices), elapsed_time)
    my_adapter_factory = HelperAdapterFactory()
    cm.input_parameter.tm_dish_dev_names = []
    stow_command = ReleaseResources(cm, cm.op_state_model, my_adapter_factory)
    assert stow_command.check_allowed() == False
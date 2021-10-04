import pytest
import tango
import time
import json
from tango.test_utils import DeviceTestContext
from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.model.enum import ModesAvailability
from ska_tango_base.control_model import HealthState, TestMode, SimulationMode, ControlMode
from tango import DevState
from ska_tango_base.obs.obs_device import SKAObsDevice
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import DEVICE_LIST, SLEEP_TIME, TIMEOUT, logger, count_faulty_devices
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from ska_tango_base.commands import ResultCode

devices_to_test = [
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_subarray_node/1"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray01"
                }
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_leaf_node/d0001"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_master"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_master"
                }
            ]
        },
        {
            "class": CentralNode,
            "devices": [
                {
                    "name": "ska_mid/tm_central/central_node",
                    "properties": {
                        "CspMasterLeafNodeFQDN": ["ska_mid/tm_leaf_node/csp_master"],
                        "SdpMasterLeafNodeFQDN": ["ska_mid/tm_leaf_node/sdp_master"],
                        "DishLeafNodePrefix": ["ska_mid/tm_leaf_node/d"],
                        "TMMidSubarrayNodes": ["ska_mid/tm_subarray_node/1"],
                        "TMMidCspSubarrayLeafNodes": ["ska_mid/tm_leaf_node/csp_subarray01"],
                        "TMMidSdpSubarrayLeafNodes": ["ska_mid/tm_leaf_node/sdp_subarray01"],
                        "NumDishes": [1]
                    },
                }
            ],
        }
    ]

def checked_devices(json_model):
    result = 0
    for dev in json_model["devices"]:
        if int(dev["ping"]) > 0 and dev["faulty"] == 'False':
            result += 1
    return result

def test_on_command(multi_device_tango_context):
    # import debugpy; debugpy.debug_this_thread()
    logger.info("%s", multi_device_tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")
    central_node.set_timeout_millis(30000000)
    json_model = json.loads(central_node.InternalModel)
    start_time = time.time()
    while checked_devices(json_model) != 6:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        json_model = json.loads(central_node.InternalModel)
    (result, unique_id) = central_node.On()
    logger.info(result)
    logger.info(unique_id)
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.CommandExecuted) != 2:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.CommandExecuted:
        if command[0] == unique_id[0]:
            assert command[2] == "ResultCode.OK"

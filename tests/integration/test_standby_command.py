import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from tango import DevState

from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import SLEEP_TIME, TIMEOUT, logger

devices_to_test = [
    {
        "class": HelperSubArrayDevice,
        "devices": [
            {"name": "ska_mid/tm_subarray_node/1"},
            {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
            {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
        ],
    },
    {
        "class": HelperStateDevice,
        "devices": [
            {"name": "ska_mid/tm_leaf_node/csp_master"},
            {"name": "mid_csp/elt/master"},
            {"name": "ska_mid/tm_leaf_node/sdp_master"},
            {"name": "mid_sdp/elt/master"},
            {"name": "mid_d0001/elt/master"},
            {"name": "ska_mid/tm_leaf_node/d0001"},
        ],
    },
    {
        "class": CentralNode,
        "devices": [
            {
                "name": "ska_mid/tm_central/central_node",
                "properties": {
                    "CspMasterLeafNodeFQDN": [
                        "ska_mid/tm_leaf_node/csp_master"
                    ],
                    "CspMasterFQDN": ["mid_csp/elt/master"],
                    "SdpMasterLeafNodeFQDN": [
                        "ska_mid/tm_leaf_node/sdp_master"
                    ],
                    "SdpMasterFQDN": ["mid_sdp/elt/master"],
                    "DishLeafNodePrefix": ["ska_mid/tm_leaf_node/d"],
                    "TMMidSubarrayNodes": ["ska_mid/tm_subarray_node/1"],
                    "TMMidCspSubarrayLeafNodes": [
                        "ska_mid/tm_leaf_node/csp_subarray01"
                    ],
                    "TMMidSdpSubarrayLeafNodes": [
                        "ska_mid/tm_leaf_node/sdp_subarray01"
                    ],
                    "NumDishes": [1],
                },
            }
        ],
    },
]


def checked_devices(json_model):
    result = 0
    for dev in json_model["devices"]:
        if int(dev["ping"]) > 0 and dev["faulty"] == "False":
            result += 1
    return result


@pytest.mark.post_deployment
def test_standby_command(multi_device_tango_context):
    pytest.num_events_arrived = 0

    def event_callback(evt):
        assert not evt.err
        pytest.num_events_arrived += 1

    logger.info("%s", multi_device_tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "InternalModel",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    json_model = json.loads(central_node.InternalModel)
    start_time = time.time()
    checked_devs = checked_devices(json_model)
    while checked_devs != 9:
        new_checked_devs = checked_devices(json_model)
        if checked_devs != new_checked_devs:
            checked_devs = new_checked_devs
            logger.debug("checked devices: %s", checked_devs)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        json_model = json.loads(central_node.InternalModel)
    initial_len = len(central_node.CommandExecuted)
    (result, unique_id) = central_node.On()
    (result, unique_id) = central_node.Standby()
    logger.info("Result is: %s", result)
    logger.info("Unique id: %s", unique_id)
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.CommandExecuted) != initial_len + 2:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.CommandExecuted:
        if command[0] == unique_id[0]:
            if command[2] != "ResultCode.OK":
                logger.error("Message: %s", command[3])
            assert command[2] == "ResultCode.OK"

    start_time = time.time()
    while pytest.num_events_arrived <= 2:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.num_events_arrived > 1

    csp_master = dev_factory.get_device("mid_csp/elt/master")
    csp_master.SetDirectState(DevState.STANDBY)
    # sdp_master = dev_factory.get_device("mid_sdp/elt/master")
    # sdp_master.SetDirectState(DevState.STANDBY)
    # dish_master.SetDirectState(DevState.STANDBY)
    # dish_master = dev_factory.get_device("mid_d0001/elt/master")

    start_time = time.time()
    while central_node.telescopeState != DevState.STANDBY:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert central_node.telescopeState == DevState.STANDBY

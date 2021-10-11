import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
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
def test_telescope_health_state(multi_device_tango_context):
    # import debugpy; debugpy.debug_this_thread()
    pytest.event_arrived = False

    def event_callback(evt):
        assert not evt.err
        logger.info(evt.attr_value.value)
        if evt.attr_value.value == HealthState.DEGRADED:
            pytest.event_arrived = True

    logger.info("%s", multi_device_tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "telescopeHealthState",
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
        # logger.info("%s", json_model)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        json_model = json.loads(central_node.InternalModel)

    sdp_master = dev_factory.get_device("mid_sdp/elt/master")
    sdp_master.SetDirectHealthState(HealthState.DEGRADED)

    start_time = time.time()
    while not pytest.event_arrived:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.event_arrived

    assert central_node.telescopeHealthState == HealthState.DEGRADED

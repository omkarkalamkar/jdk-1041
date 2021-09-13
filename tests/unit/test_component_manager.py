import pytest
import logging
import time
from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.manager.component_manager import CNComponentManager
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel

logger = logging.getLogger(__name__)

SLEEP_TIME = 1
TIMEOUT = 60

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": CentralNode,
            "devices": [
                {
                    "name": "ska_mid/tm_central/central_node",
                    "properties": {
                        "CspMasterLeafNodeFQDN": [
                            "ska_mid/tm_leaf_node/csp_master",
                        ],
                        "CspMasterFQDN": [
                            "mid_csp/elt/master",
                        ],
                        "SdpMasterLeafNodeFQDN": [
                            "ska_mid/tm_leaf_node/sdp_master",
                        ],
                        "SdpMasterFQDN": [
                            "mid_sdp/elt/master",
                        ],
                        "DishLeafNodePrefix": [
                            "ska_mid/tm_leaf_node/d",
                        ],
                        "TMMidSubarrayNodes": [
                            "ska_mid/tm_subarray_node/1",
                            "ska_mid/tm_subarray_node/2",
                            "ska_mid/tm_subarray_node/3",
                        ],
                        "TMMidCspSubarrayLeafNodes": [
                            "ska_mid/tm_leaf_node/csp_subarray01",
                            "ska_mid/tm_leaf_node/csp_subarray02",
                            "ska_mid/tm_leaf_node/csp_subarray03",
                        ],
                        "TMMidSdpSubarrayLeafNodes": [
                            "ska_mid/tm_leaf_node/sdp_subarray01",
                            "ska_mid/tm_leaf_node/sdp_subarray02",
                            "ska_mid/tm_leaf_node/sdp_subarray03"
                        ],
                        "NumDishes": ["10"]
                    }
                }
            ],
        }
    )

def count_faulty_devices(cm):
    result = 0
    for devInfo in cm.devices:
        if devInfo.faulty:
            result += 1
    return result

def test_all_devices_faulty(devices_to_load):
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(op_state_model, logger=logger)
    dev_list = []
    all_properties = devices_to_load["devices"][0]["properties"]
    prefix_dishes = "ska_mid/tm_leaf_node/d"
    num_dishes = 10
    for prop in all_properties:
        if prop == "DishLeafNodePrefix":
            prefix_dishes = all_properties[prop][0]
            continue
        if prop == "NumDishes":
            num_dishes = int(all_properties[prop][0])
            continue
        dev_list.append(all_properties[prop])
    cm.add_dishes(prefix_dishes, num_dishes)
    cm.add_multiple_devices(dev_list)
    start_time = time.time()
    num_faulty = count_faulty_devices(cm)
    while num_faulty != len(cm.devices):
        logger.info("Faulty devices %s", num_faulty)
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        num_faulty = count_faulty_devices(cm)
    elapsed_time = time.time() - start_time
    logger.info("checked all devices in %s", elapsed_time)
    for devInfo in cm.devices:
        assert devInfo.faulty



    
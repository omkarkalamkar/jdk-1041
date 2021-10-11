import pytest

from ska_tmc_centralnode_mid.central_node import CentralNode
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice


@pytest.fixture()
def devices_to_load():
    return (
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
    )

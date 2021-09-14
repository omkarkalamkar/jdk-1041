import logging 

logger = logging.getLogger(__name__)

SLEEP_TIME = 0.1
TIMEOUT = 3000

DishLeafNodePrefix = "ska_mid/tm_leaf_node/d"
NumDishes = 10

DEVICE_LIST = [
    "ska_mid/tm_leaf_node/csp_master",
    "mid_csp/elt/master",
    "ska_mid/tm_leaf_node/sdp_master",
    "mid_sdp/elt/master",
    "ska_mid/tm_subarray_node/1",
    "ska_mid/tm_subarray_node/2",
    "ska_mid/tm_subarray_node/3",
    "ska_mid/tm_leaf_node/csp_subarray01",
    "ska_mid/tm_leaf_node/csp_subarray02",
    "ska_mid/tm_leaf_node/csp_subarray03",
    "ska_mid/tm_leaf_node/sdp_subarray01",
    "ska_mid/tm_leaf_node/sdp_subarray02",
    "ska_mid/tm_leaf_node/sdp_subarray03"
]
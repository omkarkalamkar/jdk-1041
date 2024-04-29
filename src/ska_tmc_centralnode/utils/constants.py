"""Common constant used in centralnode
"""
from ska_control_model.result_code import ResultCode

REQUIRED_LOW_ASSIGN_RESOURCE_KEYS = ["subarray_id", "sdp"]
REQUIRED_LOW_RELEASE_RESOURCE_KEYS = ["subarray_id"]
MCCS_REQUIRED_KEYS = ["subarray_beam_ids", "station_ids", "channel_blocks"]
MID_CSP_MLN_DEVICE = "ska_mid/tm_leaf_node/csp_master"
LOW_CSP_MLN_DEVICE = "ska_low/tm_leaf_node/csp_master"
MID_SDP_MLN_DEVICE = "ska_mid/tm_leaf_node/sdp_master"
LOW_SDP_MLN_DEVICE = "ska_low/tm_leaf_node/sdp_master"
MCCS_MLN_DEVICE = "ska_low/tm_leaf_node/mccs_master"
MCCS_MLN_SUFIX = "tm_leaf_node/mccs_master"
DISH_LEAF_NODE_PREFIX = "ska_mid/tm_leaf_node/d"
DISH_LEAF_NODE_1 = "ska_mid/tm_leaf_node/d0001"
MID_SDP_MASTER_DEVICE = "mid-sdp/control/0"
MID_CSP_MASTER_DEVICE = "mid-csp/control/0"
LOW_SDP_MASTER_DEVICE = "low-sdp/control/0"
LOW_CSP_MASTER_DEVICE = "low-csp/control/0"
MCCS_MASTER_DEVICE = "low-mccs/control/control"
CENTRALNODE_MID = "ska_mid/tm_central/central_node"
mccs_release_interface = (
    "https://schema.skatelescope.org/ska-low-mccs-controller-release/2.0"
)

DISH_VCC_VALIDATION_RESULT_STATUS = {
    ResultCode.FAILED: "TMC and CSP Master Dish VCC version is Different",
    ResultCode.NOT_ALLOWED: "CSP Master device is unavailable",
    ResultCode.OK: "TMC and CSP Master Dish Vcc Version is Same",
}

DISH_KVALUE_VALIDATION_RESULT_STATUS = {
    ResultCode.FAILED: "k-value not identical",
    ResultCode.NOT_ALLOWED: "Dish Unavailable",
    ResultCode.OK: "k-value identical",
    ResultCode.UNKNOWN: "k-value not set",
    ResultCode.STARTED: "Dish leaf node initializing",
}


DISH_VCC_CONFIG_INTERFACE_VERSION = (
    "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0"
)

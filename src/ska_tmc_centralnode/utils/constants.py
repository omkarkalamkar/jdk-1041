"""Common constant used in centralnode"""
from ska_control_model.result_code import ResultCode

MID_CSP_MLN_DEVICE = "mid-tmc/leaf-node-csp/0"
LOW_CSP_MLN_DEVICE = "low-tmc/leaf-node-csp/0"
MID_SDP_MLN_DEVICE = "mid-tmc/leaf-node-sdp/0"
LOW_SDP_MLN_DEVICE = "low-tmc/leaf-node-sdp/0"
MCCS_MLN_DEVICE = "low-tmc/leaf-node-mccs/0"
DISH_LEAF_NODE_PREFIX = "mid-tmc/leaf-node-dish/ska"
DISH_LEAF_NODE_1 = "mid-tmc/leaf-node-dish/ska001"
DISH_LEAF_NODE_36 = "mid-tmc/leaf-node-dish/ska036"
DISH_LEAF_NODE_63 = "mid-tmc/leaf-node-dish/ska063"
DISH_LEAF_NODE_100 = "mid-tmc/leaf-node-dish/ska100"
DISH_LEAF_NODE_099 = "mid-tmc/leaf-node-dish/ska099"
DISH_LEAF_NODE_500 = "mid-tmc/leaf-node-dish/ska500"
DISH_LEAF_NODE_999 = "mid-tmc/leaf-node-dish/ska999"
DISH_LEAF_NODE_MKT = "mid-tmc/leaf-node-dish/mkt001"
MID_SDP_MASTER_DEVICE = "mid-sdp/control/0"
MID_CSP_MASTER_DEVICE = "mid-csp/control/0"
LOW_SDP_MASTER_DEVICE = "low-sdp/control/0"
LOW_CSP_MASTER_DEVICE = "low-csp/control/0"
MCCS_MASTER_DEVICE = "low-mccs/control/control"
CENTRALNODE_MID = "mid-tmc/central-node/0"
CENTRALNODE_LOW = "low-tmc/central-node/0"
LOW_TMC_SUBARRAY = "low-tmc/subarray/01"
MID_TMC_SUBARRAY = "mid-tmc/subarray/01"
LOW_CSP_SUBARRAY_LN = "low-tmc/subarray-leaf-node-csp/01"
LOW_SDP_SUBARRAY_LN = "low-tmc/subarray-leaf-node-sdp/01"
MID_CSP_SUBARRAY_LN = "mid-tmc/subarray-leaf-node-csp/01"
MID_SDP_SUBARRAY_LN = "mid-tmc/subarray-leaf-node-sdp/01"
LOW_CSP_SUBARRAY = "low-csp/subarray/01"
LOW_SDP_SUBARRAY = "low-sdp/subarray/01"
DISH_DEVICE_PREFIX = "mid-dish/dish-manager"
DISH_MASTER_1 = "mid-dish/dish-manager/ska001"
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
ARRAY_LAYOUT_DEFAULT_MID = {
    "source_uris": [
        "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
    ],
    "array_layout_path": "instrument/ska1_mid/layout/mid-layout.json",
}
ARRAY_LAYOUT_DEFAULT_LOW = {
    "source_uris": [
        "gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata"
    ],
    "array_layout_path": "instrument/ska1_low/layout/low-layout.json",
}

DISH_VCC_CONFIG_INTERFACE_VERSION = (
    "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0"
)

LOW_ASSIGN_RESOURCES_SCHEMA_VERSION = (
    "https://schema.skao.int/ska-low-tmc-assignresources/4.1"
)

LOW_RELEASE_RESOURCES_SCHEMA_VERSION = (
    "https://schema.skao.int/ska-low-tmc-releaseresources/3.0"
)

SUB_SYSTEMS = {"mccs", "csp", "sdp"}

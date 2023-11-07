"""Common constant used in centralnode
"""
REQUIRED_LOW_ASSIGN_RESOURCE_KEYS = ["subarray_id", "sdp"]
REQUIRED_LOW_RELEASE_RESOURCE_KEYS = ["subarray_id"]
MCCS_REQUIRED_KEYS = ["subarray_beam_ids", "station_ids", "channel_blocks"]
MID_CSP_MLN_DEVICE = "ska_mid/tm_leaf_node/csp_master"
LOW_CSP_MLN_DEVICE = "ska_low/tm_leaf_node/csp_master"
MID_SDP_MLN_DEVICE = "ska_mid/tm_leaf_node/sdp_master"
LOW_SDP_MLN_DEVICE = "ska_low/tm_leaf_node/sdp_master"
MCCS_MLN_DEVICE = "ska_low/tm_leaf_node/mccs_master"
MCCS_MLN_SUFIX = "tm_leaf_node/mccs_master"
mccs_release_interface = (
    "https://schema.skatelescope.org/ska-low-mccs-controller-release/2.0"
)

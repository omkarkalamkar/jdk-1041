"""Common constant used in centralnode
"""

REQUIRED_LOW_ASSIGN_RESOURCE_KEYS = ["subarray_id", "sdp", "csp"]
REQUIRED_LOW_RELEASE_RESOURCE_KEYS = ["subarray_id"]
REQUIRED_MID_RELEASE_RESOURCE_KEYS = [
    "subarray_id",
    "receptor_ids",
]
REQUIRED_MID_ASSIGN_RESOURCE_KEYS = [
    "subarray_id",
    "dish",
    "receptor_ids",
    "sdp",
]


MCCS_REQUIRED_KEYS = ["subarray_beam_ids", "station_ids", "channel_blocks"]

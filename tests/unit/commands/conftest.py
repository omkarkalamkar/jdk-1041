import pytest
from ska_tmc_common import HelperMCCSController, HelperMCCSMasterLeafNode
from ska_tmc_common.test_helpers.helper_base_device import HelperBaseDevice
from ska_tmc_common.test_helpers.helper_csp_master_leaf_node import (
    HelperCspMasterLeafDevice,
)
from ska_tmc_common.test_helpers.helper_dish_device import (
    HelperDishDevice,
    HelperDishLNDevice,
)
from ska_tmc_common.test_helpers.helper_sdp_master_leaf_node import (
    HelperSDPMasterLeafNode,
)
from ska_tmc_common.test_helpers.helper_subarray_leaf_device import (
    HelperSubarrayLeafDevice,
)

from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SLN_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_CONTROLLER,
    MCCS_MLN_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
    MID_SUBARRAY_DEVICE,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invocation."""
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
                {"name": MID_SUBARRAY_DEVICE},
            ],
        },
        {
            "class": HelperMCCSMasterLeafNode,
            "devices": [
                {"name": MCCS_MLN_DEVICE},
            ],
        },
        {
            "class": HelperMCCSController,
            "devices": [
                {"name": MCCS_CONTROLLER},
            ],
        },
        {
            "class": HelperSubarrayLeafDevice,
            "devices": [
                {"name": LOW_CSP_SLN_DEVICE},
                {"name": LOW_SDP_SLN_DEVICE},
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
        {
            "class": HelperCspMasterLeafDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
                {"name": LOW_CSP_MASTER_DEVICE},
                {"name": LOW_SDP_MASTER_DEVICE},
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
            ],
        },
        {
            "class": HelperSDPMasterLeafNode,
            "devices": [
                {"name": MID_SDP_MLN_DEVICE},
                {"name": LOW_SDP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperDishDevice,
            "devices": [
                {"name": DISH_MASTER_DEVICE},
            ],
        },
        {
            "class": HelperDishLNDevice,
            "devices": [
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )

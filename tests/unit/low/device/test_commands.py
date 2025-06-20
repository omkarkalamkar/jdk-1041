"""Test cases for testing commands"""

import pytest
import tango
from ska_tmc_common import (
    HelperCspMasterLeafDevice,
    HelperMCCSMasterLeafNode,
    HelperSDPMasterLeafNode,
)

from ska_tmc_centralnode.central_node_low import LowTmcCentralNode
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_MLN_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
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
            "class": HelperCspMasterLeafDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
                {"name": MID_CSP_MLN_DEVICE},
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
            "class": LowTmcCentralNode,
            "devices": [
                {
                    "name": "low-tmc/central-node/0",
                    "properties": {
                        "CspMasterLeafNodeFQDN": LOW_CSP_MLN_DEVICE,
                        "SdpMasterLeafNodeFQDN": LOW_SDP_MLN_DEVICE,
                        "MCCSMasterLeafNodeFQDN": MCCS_MLN_DEVICE,
                    },
                },
            ],
        },
    )


@pytest.mark.SKA_low
def test_commands(tango_context):
    """Test Command for low telescope"""
    central_node_device = tango.DeviceProxy("low-tmc/central-node/0")
    try:
        central_node_device.TelescopeOn()
        central_node_device.TelescopeOff()
        central_node_device.off()

    except Exception as ex:
        assert "CommandNotAllowed" in str(ex)

    with pytest.raises(Exception):
        central_node_device.StartUpTelescope()
        central_node_device.StandByTelescope()
        central_node_device.Standby()
        central_node_device.TelescopeStandby()

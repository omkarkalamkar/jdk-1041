import pytest
from ska_control_model import AdminMode
from ska_tmc_common import HelperCspMasterLeafDevice, HelperSDPMasterLeafNode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_centralnode.model.input import InputParameterMid
from tests.settings import MID_CSP_MLN_DEVICE, MID_SDP_MLN_DEVICE, create_cm


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invokations."""
    return (
        {
            "class": HelperCspMasterLeafDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperSDPMasterLeafNode,
            "devices": [
                {"name": MID_SDP_MLN_DEVICE},
            ],
        },
    )


@pytest.mark.parametrize(
    "sdp, csp, should_raise",
    [
        # All valid
        (AdminMode.ONLINE, AdminMode.ONLINE, False),
        # One or more invalid
        (AdminMode.OFFLINE, AdminMode.ONLINE, True),
        (AdminMode.ONLINE, AdminMode.NOT_FITTED, True),
        (AdminMode.NOT_FITTED, AdminMode.NOT_FITTED, True),
        (AdminMode.OFFLINE, AdminMode.NOT_FITTED, True),
        (AdminMode.NOT_FITTED, AdminMode.ONLINE, True),
    ],
)
def test_low_admin_mode_validation_without_mccs(
    tango_context, sdp, csp, should_raise
):
    """Test validation of admin modes for SDP and CSP only."""
    cm, _ = create_cm(_input_parameter=InputParameterMid(None))
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    proxy_sdp_mln = dev_factory.get_device(MID_SDP_MLN_DEVICE)

    proxy_csp_mln.SetCspControllerAdminMode(csp)
    proxy_sdp_mln.SetSdpControllerAdminMode(sdp)

    if should_raise:
        with pytest.raises(CommandNotAllowed):
            cm.is_command_allowed()
    else:
        cm.is_command_allowed()

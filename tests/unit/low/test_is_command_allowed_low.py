import pytest
from ska_control_model import AdminMode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import (
    CommandNotAllowed,
    SubarrayNotPresentError,
)
from ska_tmc_simulators import (
    HelperCspMasterLeafDevice,
    HelperMCCSMasterLeafNode,
    HelperSDPMasterLeafNode,
)

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.settings import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MCCS_MLN_DEVICE,
    create_cm,
    logger,
)


@pytest.fixture()
def devices_to_load():
    """Devices to load for command invokations."""
    return (
        {
            "class": HelperCspMasterLeafDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperSDPMasterLeafNode,
            "devices": [
                {"name": LOW_SDP_MLN_DEVICE},
            ],
        },
        {
            "class": HelperMCCSMasterLeafNode,
            "devices": [
                {"name": MCCS_MLN_DEVICE},
            ],
        },
    )


@pytest.mark.parametrize(
    "sdp, csp, mccs, should_raise",
    [
        # All valid
        (AdminMode.ONLINE, AdminMode.ONLINE, AdminMode.ONLINE, False),
        # One or more invalid,
        (AdminMode.ONLINE, AdminMode.NOT_FITTED, AdminMode.ONLINE, True),
        (AdminMode.OFFLINE, AdminMode.ONLINE, AdminMode.ONLINE, True),
        (AdminMode.ONLINE, AdminMode.ONLINE, AdminMode.NOT_FITTED, True),
        (AdminMode.ONLINE, AdminMode.ONLINE, AdminMode.OFFLINE, True),
        (
            AdminMode.NOT_FITTED,
            AdminMode.NOT_FITTED,
            AdminMode.NOT_FITTED,
            True,
        ),
        (AdminMode.ONLINE, AdminMode.OFFLINE, AdminMode.OFFLINE, True),
        (AdminMode.OFFLINE, AdminMode.NOT_FITTED, AdminMode.ONLINE, True),
        (AdminMode.OFFLINE, AdminMode.ONLINE, AdminMode.NOT_FITTED, True),
        (AdminMode.ONLINE, AdminMode.ONLINE, AdminMode.OFFLINE, True),
    ],
)
def test_low_admin_mode_validation_only(
    tango_context, sdp, csp, mccs, should_raise
):
    """Test validation of admin modes without command-specific checks."""

    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    proxy_sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    proxy_mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)

    proxy_csp_mln.SetCspControllerAdminMode(csp)
    proxy_sdp_mln.SetSdpControllerAdminMode(sdp)
    proxy_mccs_mln.SetMccsControllerAdminMode(mccs)

    if should_raise:
        with pytest.raises(CommandNotAllowed):
            cm.is_command_allowed()
    else:
        assert cm.is_command_allowed() is True


def test_check_device_responsiveness_command(tango_context):
    cm, _ = create_cm(_input_parameter=InputParameterLow(None))
    device_name = "low-tmc/subarray/01"
    for dev_info in cm.component.devices:
        if device_name in dev_info.dev_name:
            dev_info.update_unresponsive(True)
            logger.info("Device unresponsive flag: %s", dev_info.unresponsive)

    with pytest.raises(SubarrayNotPresentError):
        cm.cmd_allowed_validator.check_device_responsiveness_command(
            "AssignResources", 1
        )

"""Test case module"""
import pytest
import tango
from ska_tmc_common import (
    HelperBaseDevice,
    HelperMCCSController,
    HelperMCCSMasterLeafNode,
)
from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.cn_helper_subarray_device import CNHelperSubArrayDevice
from tests.settings import (
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SLN_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    MCCS_CONTROLLER,
    MCCS_MLN_DEVICE,
    create_cm_no_faulty_devices,
    ensure_telescope_state,
    set_devices_state,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": CNHelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
                {"name": LOW_SDP_SLN_DEVICE},
                {"name": LOW_CSP_SLN_DEVICE},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
                {"name": LOW_CSP_MASTER_DEVICE},
                {"name": LOW_SDP_MLN_DEVICE},
                {"name": LOW_SDP_MASTER_DEVICE},
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
    )


@pytest.mark.SKA_low
def test_telescope_state_off(tango_context):
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_devices_state(
        devices=[
            "low-sdp/control/0",
            "low-csp/control/0",
            "low-mccs/control/control",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.OFF,
    )
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=30)
    assert cm.component.telescope_state == tango.DevState.OFF

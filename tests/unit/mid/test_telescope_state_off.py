import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    MID_CSP_CONTROL_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_SUBARRAY_DEVICE,
    MID_SDP_CONTROL_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_SUBARRAY_DEVICE,
    MID_SUBARRAY_DEVICE,
    TMC_DISH1_DEVICE,
    TMC_DISH2_DEVICE,
    create_cm_no_faulty_devices,
    ensure_telescope_state,
    set_devices_state,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
                {"name": MID_CSP_SUBARRAY_DEVICE},
                {"name": MID_SDP_SUBARRAY_DEVICE},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_CSP_CONTROL_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
                {"name": MID_SDP_CONTROL_DEVICE},
                {"name": TMC_DISH2_DEVICE},
                {"name": TMC_DISH1_DEVICE},
            ],
        },
    )


def test_telescope_state_off(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_state(
        devices=[
            "mid-csp/control/0",
            "mid-sdp/control/0",
            "mid_d0001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.OFF
        # Here expected elapsed time is set to 12 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    )
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=12)
    assert cm.component.telescope_state == tango.DevState.OFF

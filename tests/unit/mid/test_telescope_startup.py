import pytest
import tango
from ska_tango_base.control_model import HealthState
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


def test_aggregation_default(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    assert cm.component.telescope_state == tango.DevState.UNKNOWN
    assert cm.component.tmc_op_state == tango.DevState.UNKNOWN
    assert cm.component.telescope_health_state in [
        HealthState.UNKNOWN,
        HealthState.OK,
    ]

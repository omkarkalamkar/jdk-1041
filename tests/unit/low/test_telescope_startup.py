import pytest
import tango
from ska_tango_base.control_model import HealthState
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    LOW_CSP_MASTER_DEVICE,
    LOW_CSP_MLN_DEVICE,
    LOW_CSP_SLN_DEVICE,
    LOW_SDP_MASTER_DEVICE,
    LOW_SDP_MLN_DEVICE,
    LOW_SDP_SLN_DEVICE,
    LOW_SUBARRAY_DEVICE,
    create_cm_no_faulty_devices,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": LOW_SUBARRAY_DEVICE},
                {"name": LOW_SDP_SLN_DEVICE},
                {"name": LOW_CSP_SLN_DEVICE},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
                {"name": LOW_CSP_MASTER_DEVICE},
                {"name": LOW_SDP_MLN_DEVICE},
                {"name": LOW_SDP_MASTER_DEVICE},
            ],
        },
    )


@pytest.mark.SKA_low
def test_aggregation_default(tango_context):
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    assert cm.component.telescope_state == tango.DevState.UNKNOWN
    assert cm.component.tmc_op_state == tango.DevState.UNKNOWN
    assert cm.component.telescope_health_state in [
        HealthState.UNKNOWN,
        HealthState.OK,
    ]

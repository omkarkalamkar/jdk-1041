import pytest
import tango
from ska_tango_base.control_model import HealthState
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import create_cm_no_faulty_devices


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": "ska_low/tm_subarray_node/1"},
                {"name": "ska_low/tm_leaf_node/mccs_subarray01"},
            ],
        },
        {
            "class": HelperMCCSStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
                {"name": "low-mccs/control/control"},
            ],
        },
    )


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

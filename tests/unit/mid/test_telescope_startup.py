import pytest
import tango
from ska_tango_base.control_model import HealthState
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import create_cm_no_faulty_devices


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": "ska_mid/tm_subarray_node/1"},
                {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
                {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "mid-csp/control/0"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "mid-sdp/control/0"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
                {"name": "mid_d0001/elt/master"},
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

import pytest
import tango
from ska_tango_base.control_model import HealthState
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.test_helpers.helper_subarray_leaf_device import (
    HelperSubarrayLeafDevice,
)

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import create_cm_no_faulty_devices


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperMCCSStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_master"},
                {"name": "low-mccs/control/control"},
            ],
        },
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": "ska_low/tm_subarray_node/1"},
            ],
        },
        {
            "class": SKABaseDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/csp_master"},
                {"name": "low_csp/elt/master"},
                {"name": "ska_low/tm_leaf_node/sdp_master"},
                {"name": "low_sdp/elt/master"},
            ],
        },
        {
            "class": HelperSubarrayLeafDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/mccs_subarray01"},
                {"name": "ska_low/tm_leaf_node/csp_subarray01"},
                {"name": "ska_low/tm_leaf_node/sdp_subarray01"},
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

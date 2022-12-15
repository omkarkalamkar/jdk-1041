import pytest
import tango
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_mccsdevice import (
    HelperMCCSStateDevice,
)
from ska_tmc_common.test_helpers.helper_subarray_leaf_device import (
    HelperSubarrayLeafDevice,
)

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    create_cm_no_faulty_devices,
    ensure_telescope_state,
    set_device_state,
)


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


def test_telescope_state_off(tango_context):
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_device_state(
        "low-mccs/control/control",
        devFactory=DevFactory(),
        state=tango.DevState.OFF,
    )
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=15)
    assert cm.component.telescope_state == tango.DevState.OFF

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

from ska_tmc_centralnode.model.enum import ModesAvailability
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    MID_SUBARRAY_DEVICE,
    create_cm_no_faulty_devices,
    ensure_imaging,
    set_devices_state,
)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
            "devices": [
                {"name": MID_SUBARRAY_DEVICE},
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
                {"name": "mid_d0001/elt/master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def test_imaging_available(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_state(
        devices=[
            "mid-csp/control/0",
            "mid_d0001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.ON,
    )
    ensure_imaging(cm, ModesAvailability.available, expected_elapsed_time=12)
    # Here expected elapsed time is set to 12 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    assert cm.component.imaging == ModesAvailability.available

import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
    MID_SUBARRAY_DEVICE,
    create_cm_no_faulty_devices,
    ensure_tmc_op_state,
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
                {"name": "mid-csp/control/0"},
                {"name": "mid-sdp/control/0"},
                {"name": "mid_d0001/elt/master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
            ],
        },
    )


def set_devices_on(cm, devFactory, expected_elapsed_time):
    set_devices_state(
        devices=[
            "ska_mid/tm_subarray_node/1",
            "ska_mid/tm_leaf_node/csp_subarray01",
            "ska_mid/tm_leaf_node/sdp_subarray01",
            "ska_mid/tm_leaf_node/csp_master",
            "ska_mid/tm_leaf_node/sdp_master",
            "ska_mid/tm_leaf_node/d0001",
        ],
        devFactory=devFactory,
        state=tango.DevState.ON,
    )
    ensure_tmc_op_state(cm, tango.DevState.ON, expected_elapsed_time)


@pytest.mark.skip(reason="behaviour for this test case is not stable")
def test_tmc_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_on(
        cm, devFactory, 20
    )  # Here expected elapsed time is set to 20 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    assert cm.component.tmc_op_state == tango.DevState.ON

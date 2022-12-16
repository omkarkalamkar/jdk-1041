import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice
from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
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
                {"name": "ska_low/tm_subarray_node/1"},
                {"name": "ska_low/tm_leaf_node/sdp_subarray01"},
                {"name": "ska_low/tm_leaf_node/csp_subarray01"},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": "ska_low/tm_leaf_node/csp_master"},
                {"name": "low-csp/control/0"},
                {"name": "ska_low/tm_leaf_node/sdp_master"},
                {"name": "low-sdp/control/0"},
            ],
        },
    )


def set_devices_on(cm, devFactory, expected_elapsed_time):
    set_devices_state(
        devices=[
            "low-sdp/control/0",
            "low-csp/control/0",     
        ],
        devFactory=devFactory,
        state=tango.DevState.ON
    )
    ensure_telescope_state(cm, tango.DevState.ON, expected_elapsed_time=12)

@pytest.mark.devesh
def test_telescope_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_devices_on(cm, devFactory, 15)
    assert cm.component.telescope_state == tango.DevState.ON

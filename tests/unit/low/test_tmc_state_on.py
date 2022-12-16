import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

from ska_tmc_centralnode.model.input import InputParameterLow
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
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
                {"name": "ska_low/tm_subarray_node/1"},
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
            "ska_low/tm_subarray_node/1",
            "ska_low/tm_leaf_node/mccs_subarray01",
            "ska_low/tm_leaf_node/mccs_master",
        ],
        devFactory=devFactory,
        state=tango.DevState.ON,
    )
    ensure_tmc_op_state(cm, tango.DevState.ON, expected_elapsed_time)


@pytest.mark.skip(reason="behaviour for this test case is not stable")
def test_tmc_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_devices_on(
        cm, devFactory, 20
    )  # Here expected elapsed time is set to 20 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    assert cm.component.tmc_op_state == tango.DevState.ON

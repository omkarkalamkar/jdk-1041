import pytest
import tango
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.dev_factory import DevFactory

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
    ensure_tmc_op_state,
    set_devices_state,
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
            "class": HelperBaseDevice,
            "devices": [
                {"name": LOW_CSP_MLN_DEVICE},
                {"name": LOW_CSP_MASTER_DEVICE},
                {"name": LOW_SDP_MLN_DEVICE},
                {"name": LOW_SDP_MASTER_DEVICE},
            ],
        },
    )


def set_devices_on(cm, devFactory, expected_elapsed_time):
    set_devices_state(
        devices=[
            "ska_low/tm_subarray_node/1",
            "ska_low/tm_leaf_node/sdp_master",
            "ska_low/tm_leaf_node/csp_master",
            "ska_low/tm_leaf_node/csp_subarray01",
            "ska_low/tm_leaf_node/sdp_subarray01",
        ],
        devFactory=devFactory,
        state=tango.DevState.ON,
    )
    ensure_tmc_op_state(cm, tango.DevState.ON, expected_elapsed_time)


@pytest.mark.SKA_low
def test_tmc_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(
        tango_context, True, True, InputParameterLow(None)
    )
    set_devices_on(
        cm, devFactory, 25
    )  # Here expected elapsed time is set to 25 since  set_state() API is taking more time to set the state and hence actual elapsed time is increasing
    assert cm.component.tmc_op_state == tango.DevState.ON

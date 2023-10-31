import pytest
import tango
from ska_tmc_common import HelperBaseDevice
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)

from ska_tmc_centralnode.model.enum import ModesAvailability
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    MID_CSP_MASTER_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_CSP_SLN_DEVICE,
    MID_SDP_MASTER_DEVICE,
    MID_SDP_MLN_DEVICE,
    MID_SDP_SLN_DEVICE,
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
                {"name": MID_CSP_SLN_DEVICE},
                {"name": MID_SDP_SLN_DEVICE},
            ],
        },
        {
            "class": HelperBaseDevice,
            "devices": [
                {"name": MID_CSP_MLN_DEVICE},
                {"name": MID_CSP_MASTER_DEVICE},
                {"name": MID_SDP_MLN_DEVICE},
                {"name": MID_SDP_MASTER_DEVICE},
                {"name": DISH_MASTER_DEVICE},
                {"name": DISH_LEAF_NODE_DEVICE},
            ],
        },
    )


def test_imaging_not_available(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_state(
        devices=[
            "mid-csp/control/0",
            "ska001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.OFF,
    )
    ensure_imaging(
        cm, ModesAvailability.not_available, expected_elapsed_time=1.5
    )
    assert cm.component.imaging == ModesAvailability.not_available

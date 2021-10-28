import pytest
import tango

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from ska_tmc_centralnode_mid.model.enum import ModesAvailability
from tests.helpers.helper_state_device import HelperStateDevice
from tests.helpers.helper_subarray_device import HelperSubArrayDevice
from tests.settings import (
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
                {"name": "ska_mid/tm_subarray_node/1"},
                {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
                {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": "ska_mid/tm_leaf_node/csp_master"},
                {"name": "mid_csp/elt/master"},
                {"name": "ska_mid/tm_leaf_node/sdp_master"},
                {"name": "mid_sdp/elt/master"},
                {"name": "mid_d0001/elt/master"},
                {"name": "ska_mid/tm_leaf_node/d0001"},
            ],
        },
    )


def test_imaging_available(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_state(
        devices=[
            "mid_csp/elt/master",
            "mid_d0001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.ON,
        cm=cm,
        expected_elapsed_time=1.5,
    )
    ensure_imaging(cm, ModesAvailability.available, expected_elapsed_time=1.5)
    assert cm.component.imaging == ModesAvailability.available


def test_imaging_available_only_monitoring_loop(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_devices_state(
        devices=[
            "mid_csp/elt/master",
            "mid_d0001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.ON,
        cm=cm,
        expected_elapsed_time=1.5,
    )
    ensure_imaging(cm, ModesAvailability.available, expected_elapsed_time=1.5)
    assert cm.component.imaging == ModesAvailability.available


def test_imaging_available_only_events(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_devices_state(
        devices=[
            "mid_csp/elt/master",
            "mid_d0001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.ON,
        cm=cm,
        expected_elapsed_time=2,
    )
    ensure_imaging(cm, ModesAvailability.available, expected_elapsed_time=2)
    assert cm.component.imaging == ModesAvailability.available

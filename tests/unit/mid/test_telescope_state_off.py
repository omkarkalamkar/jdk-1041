import pytest
import tango
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.test_helpers.helper_state_device import HelperStateDevice

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

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_state_off(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_state(
        devices=[
            "mid_csp/elt/master",
            "mid_sdp/elt/master",
            "mid_d0001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.OFF,
        cm=cm,
        expected_elapsed_time=1.5,
    )
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=1.5)
    assert cm.component.telescope_state == tango.DevState.OFF

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_state_off_only_monitoring_loop(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_devices_state(
        devices=[
            "mid_csp/elt/master",
            "mid_sdp/elt/master",
            "mid_d0001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.OFF,
        cm=cm,
        expected_elapsed_time=1.5,
    )
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=1.5)
    assert cm.component.telescope_state == tango.DevState.OFF

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
def test_telescope_state_off_only_events(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_devices_state(
        devices=[
            "mid_csp/elt/master",
            "mid_sdp/elt/master",
            "mid_d0001/elt/master",
        ],
        devFactory=DevFactory(),
        state=tango.DevState.OFF,
        cm=cm,
        expected_elapsed_time=2,
    )
    ensure_telescope_state(cm, tango.DevState.OFF, expected_elapsed_time=2)
    assert cm.component.telescope_state == tango.DevState.OFF

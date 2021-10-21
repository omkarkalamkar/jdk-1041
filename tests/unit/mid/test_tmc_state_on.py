import pytest
import tango

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
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
                {"name": "ska_mid/tm_subarray_node/1"},
                {"name": "ska_mid/tm_leaf_node/csp_subarray01"},
                {"name": "ska_mid/tm_leaf_node/sdp_subarray01"},
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {"name": "mid_csp/elt/master"},
                {"name": "mid_sdp/elt/master"},
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
        cm=cm,
        expected_elapsed_time=expected_elapsed_time,
    )
    ensure_tmc_op_state(cm, tango.DevState.ON, expected_elapsed_time)


def test_tmc_state_on(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.ON


def test_tmc_state_on_only_monitoring_loop(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, True, False)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.ON


def test_tmc_state_on_only_events(tango_context):
    devFactory = DevFactory()
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    set_devices_on(cm, devFactory, 1.5)
    assert cm.component.tmc_op_state == tango.DevState.ON

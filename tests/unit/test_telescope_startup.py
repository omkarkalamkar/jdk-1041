
from logging import debug
from ska_tango_base.subarray import SKASubarray
import tango
import time
import pytest
from ska_tango_base.control_model import HealthState
from tests.settings import count_faulty_devices, logger, TIMEOUT
from test_cm_all_working import create_cm
from tests.helper_state_device import HelperStateDevice
from ska_tmc_centralnode_mid.dev_factory import DevFactory

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": SKASubarray,
            "devices": [
                {
                    "name": "ska_mid/tm_subarray_node/1"
                },
                {
                    "name": "ska_mid/tm_subarray_node/2"
                },
                {
                    "name": "ska_mid/tm_subarray_node/3"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray02"
                },
                {
                    "name": "ska_mid/tm_leaf_node/csp_subarray03"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray01"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray02"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_subarray03"
                }
            ],
        },
        {
            "class": HelperStateDevice,
            "devices": [
                {
                    "name": "ska_mid/tm_leaf_node/csp_master"
                },
                {
                    "name": "mid_csp/elt/master"
                },
                {
                    "name": "ska_mid/tm_leaf_node/sdp_master"
                },
                {
                    "name": "mid_sdp/elt/master"
                },
                {
                    "name": "mid_d0001/elt/master"
                }
            ]
        }        
    )

def create_cm_no_faulty_devices(tango_context, p_monitoring_loop, p_event_receiver):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(p_monitoring_loop, p_event_receiver)
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    return cm

def test_aggregation_default(tango_context):
    cm = create_cm_no_faulty_devices(tango_context, True, True)
    ## Why is this in fault state initially?
    assert cm.component.telescope_state == tango.DevState.FAULT
    assert cm.component.tmc_op_state == tango.DevState.FAULT
    assert cm.component.telescope_health_state == HealthState.OK

    # without monitoring loop every thing is UNKNOWN
    cm = create_cm_no_faulty_devices(tango_context, False, True)
    assert cm.component.telescope_state == tango.DevState.UNKNOWN
    assert cm.component.tmc_op_state == tango.DevState.UNKNOWN
    assert cm.component.telescope_health_state == HealthState.UNKNOWN

    cm = create_cm_no_faulty_devices(tango_context, True, False)
    assert cm.component.telescope_state == tango.DevState.FAULT
    assert cm.component.tmc_op_state == tango.DevState.FAULT
    assert cm.component.telescope_health_state == HealthState.OK

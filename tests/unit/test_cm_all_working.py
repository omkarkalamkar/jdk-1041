import pytest
import logging
import time
from ska_tango_base.control_model import HealthState

from ska_tango_base.obs.obs_device import SKAObsDevice
import tango
from ska_tmc_centralnode_mid.model.component import SubArrayDeviceInfo
from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.manager.component_manager import CNComponentManager
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel
from tests.helper_subarray_device import HelperSubArrayDevice
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from tests.settings import DEVICE_LIST, SLEEP_TIME, TIMEOUT, logger, count_faulty_devices

@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": HelperSubArrayDevice,
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
            "class": SKAObsDevice,
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

def create_cm(p_monitoring_loop = True, p_event_receiver = True):
    op_state_model = TMCOpStateModel(logger)
    cm = CNComponentManager(op_state_model, logger=logger, _monitoring_loop=p_monitoring_loop, _event_receiver=p_event_receiver)
    for dev in DEVICE_LIST:
        cm.add_device(dev)
    start_time = time.time()
    num_devices = len(DEVICE_LIST)
    if not p_monitoring_loop:
        return cm, start_time
    while num_devices != len(cm.checked_devices):
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    return cm, start_time

def test_all_working(tango_context):
    logger.info("%s", tango_context)
    # import debugpy; debugpy.debug_this_thread()
    cm, start_time = create_cm()
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0

    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    for devInfo in cm.devices:
        assert not devInfo.faulty
        if "subarray" in devInfo.dev_name.lower():
            assert isinstance(devInfo, SubArrayDeviceInfo)

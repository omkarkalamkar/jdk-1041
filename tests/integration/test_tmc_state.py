import json
import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from tango import DevState

from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from ska_tmc_centralnode_mid.model.enum import ModesAvailability
from tests.helper_state_device import HelperStateDevice
from tests.helper_subarray_device import HelperSubArrayDevice
from tests.settings import SLEEP_TIME, TIMEOUT, logger
from tests.integration.device_to_load import devices_to_load

def checked_devices(json_model):
    result = 0
    for dev in json_model["devices"]:
        if int(dev["ping"]) > 0 and dev["faulty"] == "False":
            result += 1
    return result


@pytest.mark.post_deployment
def test_tmc_state(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    pytest.event_arrived = False

    def event_callback(evt):
        assert not evt.err
        logger.info(evt.attr_value.value)
        if evt.attr_value.value == DevState.FAULT:
            pytest.event_arrived = True

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "TMOpState",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    json_model = json.loads(central_node.InternalModel)
    start_time = time.time()
    checked_devs = checked_devices(json_model)
    while checked_devs != 9:
        new_checked_devs = checked_devices(json_model)
        if checked_devs != new_checked_devs:
            checked_devs = new_checked_devs
            logger.debug("checked devices: %s", checked_devs)
        time.sleep(SLEEP_TIME)
        # logger.info("%s", json_model)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
        json_model = json.loads(central_node.InternalModel)

    csp_master_ln = dev_factory.get_device("ska_mid/tm_leaf_node/csp_master")
    sdp_master_ln = dev_factory.get_device("ska_mid/tm_leaf_node/sdp_master")
    csp_subarray_ln = dev_factory.get_device(
        "ska_mid/tm_leaf_node/csp_subarray01"
    )
    sdp_subarray_ln = dev_factory.get_device(
        "ska_mid/tm_leaf_node/sdp_subarray01"
    )
    dish_ln = dev_factory.get_device("ska_mid/tm_leaf_node/d0001")

    # set state not handled directly by central node
    csp_master_ln.SetDirectState(DevState.FAULT)
    sdp_master_ln.SetDirectState(DevState.ON)
    csp_subarray_ln.SetDirectState(DevState.ON)
    sdp_subarray_ln.SetDirectState(DevState.ON)
    dish_ln.SetDirectState(DevState.ON)

    start_time = time.time()
    while not pytest.event_arrived:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.event_arrived

    assert central_node.TMOpState == DevState.FAULT

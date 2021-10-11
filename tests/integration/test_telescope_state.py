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
from tests.integration.device_to_load import devices_to_load
from tests.settings import SLEEP_TIME, TIMEOUT, logger


def checked_devices(json_model):
    result = 0
    for dev in json_model["devices"]:
        if int(dev["ping"]) > 0 and dev["faulty"] == "False":
            result += 1
    return result


@pytest.mark.post_deployment
def test_telescope_state(tango_context):
    # import debugpy; debugpy.debug_this_thread()
    pytest.event_arrived = False

    def event_callback(evt):
        assert not evt.err
        logger.info(evt.attr_value.value)
        if evt.attr_value.value == DevState.ON:
            pytest.event_arrived = True

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device("ska_mid/tm_central/central_node")

    central_node.subscribe_event(
        "telescopeState",
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
    initial_len = len(central_node.CommandExecuted)
    (result, unique_id) = central_node.On()
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.CommandExecuted) != initial_len + 1:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.CommandExecuted:
        if command[0] == unique_id[0]:
            assert command[2] == "ResultCode.OK"

    csp_master = dev_factory.get_device("mid_csp/elt/master")
    sdp_master = dev_factory.get_device("mid_sdp/elt/master")
    csp_subarray = dev_factory.get_device(
        "ska_mid/tm_leaf_node/csp_subarray01"
    )
    sdp_subarray = dev_factory.get_device(
        "ska_mid/tm_leaf_node/sdp_subarray01"
    )
    dish_master = dev_factory.get_device("mid_d0001/elt/master")

    # set state not handled directly by central node
    csp_master.SetDirectState(DevState.ON)
    sdp_master.SetDirectState(DevState.ON)
    csp_subarray.SetDirectState(DevState.ON)
    sdp_subarray.SetDirectState(DevState.ON)
    dish_master.SetDirectState(DevState.ON)

    start_time = time.time()
    while not pytest.event_arrived:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    assert pytest.event_arrived

    # start_time = time.time()
    # while central_node.telescopeState != DevState.ON:
    #     time.sleep(SLEEP_TIME)
    #     elapsed_time = time.time() - start_time
    #     if elapsed_time > TIMEOUT:
    #         pytest.fail("Timeout occurred while executing the test")

    assert central_node.telescopeState == DevState.ON

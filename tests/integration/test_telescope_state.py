import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DevState

from tests.integration.common import devices_to_load  # noqa F401
from tests.integration.common import (
    assert_event_arrived,
    ensure_checked_devices,
)
from tests.settings import SLEEP_TIME, TIMEOUT, logger


def telescope_state(tango_context, central_node_name):
    # import debugpy; debugpy.debug_this_thread()
    pytest.event_arrived = False

    def event_callback(evt):
        assert not evt.err
        logger.info(evt.attr_value.value)
        if evt.attr_value.value == DevState.ON:
            pytest.event_arrived = True

    logger.info("%s", tango_context)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)

    event_id = central_node.subscribe_event(
        "telescopeState",
        tango.EventType.CHANGE_EVENT,
        event_callback,
        stateless=True,
    )

    ensure_checked_devices(central_node)
    initial_len = len(central_node.commandExecuted)
    (result, unique_id) = central_node.On()
    assert result[0] == ResultCode.QUEUED
    start_time = time.time()
    while len(central_node.commandExecuted) != initial_len + 1:
        time.sleep(SLEEP_TIME)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    for command in central_node.commandExecuted:
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
    mccs_master = dev_factory.get_device("low-mccs/control/control")

    # set state not handled directly by central node
    csp_master.SetDirectState(DevState.ON)
    sdp_master.SetDirectState(DevState.ON)
    csp_subarray.SetDirectState(DevState.ON)
    sdp_subarray.SetDirectState(DevState.ON)
    dish_master.SetDirectState(DevState.ON)
    mccs_master.SetDirectState(DevState.ON)

    assert_event_arrived()

    assert central_node.telescopeState == DevState.ON

    central_node.unsubscribe_event(event_id)

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_telescope_state_mid(tango_context):
    telescope_state(tango_context, "ska_mid/tm_central/central_node")

@pytest.mark.xfail(reason="Test needs update as per v0.13. Can be done as a part of further commands refactoring.")
@pytest.mark.post_deployment
@pytest.mark.SKA_low
def test_telescope_state_low(tango_context):
    telescope_state(tango_context, "ska_low/tm_central/central_node")

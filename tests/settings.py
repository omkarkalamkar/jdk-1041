import logging
import time

import pytest
#from ska_tango_base.base.base_device import _CommandTracker
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)

logger = logging.getLogger(__name__)

SLEEP_TIME = 0.5
TIMEOUT = 20

DishLeafNodePrefix = "ska_mid/tm_leaf_node/d"
NumDishes = 10

MID_SUBARRAY_DEVICE = "ska_mid/tm_subarray_node/1"
LOW_SUBARRAY_DEVICE = "ska_low/tm_subarray_node/1"


DEVICE_LIST_MID = [
    "ska_mid/tm_leaf_node/csp_master",
    "mid-csp/control/0",
    "ska_mid/tm_leaf_node/sdp_master",
    "mid-sdp/control/0",
    "ska_mid/tm_subarray_node/1",
    "ska_mid/tm_leaf_node/csp_subarray01",
    "ska_mid/tm_leaf_node/sdp_subarray01",
    "ska_mid/tm_leaf_node/d0001",
    "mid_d0001/elt/master",
]

DEVICE_LIST_LOW = [
    # "ska_low/tm_leaf_node/mccs_master",
    # "low-mccs/control/control",
    # "ska_low/tm_leaf_node/mccs_subarray01",
    "ska_low/tm_subarray_node/1",
    "low-sdp/control/0",
    "low-csp/control/0",
    "ska_low/tm_leaf_node/csp_master",
    "ska_low/tm_leaf_node/sdp_master",
    "ska_low/tm_leaf_node/csp_subarray01",
    "ska_low/tm_leaf_node/sdp_subarray01",
]


def count_faulty_devices(cm):
    result = 0
    for devInfo in cm.checked_devices:
        if devInfo.unresponsive:
            result += 1
    return result


def create_cm_mid(
    p_liveliness_probe=False,
    input_parameter=InputParameterMid(None),
):
    op_state_model = TMCOpStateModel(logger)(
        queue_changed_callback=None,
        status_changed_callback=None,
        progress_changed_callback=None,
        result_callback=None,
    )
    cm = CNComponentManagerMid(
        op_state_model,
        logger=logger,
        _input_parameter=input_parameter,
    )
    DEVICE_LIST = DEVICE_LIST_MID
    for dev in DEVICE_LIST:
        cm.add_device(dev)
    start_time = time.time()
    num_devices = len(DEVICE_LIST)
    if not p_liveliness_probe:
        return cm, start_time
    while num_devices != len(cm.checked_devices):
        time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    return cm, start_time


def create_cm_low(
    p_liveliness_probe=False,
    event_receiver=True,
    input_parameter=InputParameterLow(None),
):
    op_state_model = TMCOpStateModel(logger)(
        queue_changed_callback=None,
        status_changed_callback=None,
        progress_changed_callback=None,
        result_callback=None,
    )
    cm = CNComponentManagerLow(
        op_state_model,
        logger=logger,
        _input_parameter=input_parameter,
        _event_receiver=event_receiver,
    )
    DEVICE_LIST = DEVICE_LIST_LOW
    for dev in DEVICE_LIST:
        cm.add_device(dev)
    start_time = time.time()
    num_devices = len(DEVICE_LIST)
    if not p_liveliness_probe:
        return cm, start_time
    while num_devices != len(cm.checked_devices):
        time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")

    return cm, start_time


def create_cm_no_faulty_devices(
    tango_context,
    p_liveliness_probe,
    p_event_receiver,
    input_parameter=InputParameterMid(None),
):
    logger.info("%s", tango_context)
    if isinstance(input_parameter, InputParameterMid):
        input_parameter = InputParameterMid(None)
        cm, start_time = create_cm_mid(
            p_liveliness_probe, p_event_receiver, input_parameter
        )
    else:
        input_parameter = InputParameterLow(None)
        cm, start_time = create_cm_low(
            p_liveliness_probe, p_event_receiver, input_parameter
        )
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %s devices in %s", num_faulty, elapsed_time)
    return cm


def ensure_telescope_state(cm, state, expected_elapsed_time):
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_state != state:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time


def ensure_tmc_op_state(cm, state, expected_elapsed_time):
    start_time = time.time()
    elapsed_time = 0
    while cm.component.tmc_op_state != state:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time


def ensure_imaging(cm, value, expected_elapsed_time):
    start_time = time.time()
    elapsed_time = 0
    while cm.component.imaging != value:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time


def set_devices_state(devices, state, devFactory):
    for device in devices:
        proxy = devFactory.get_device(device)
        proxy.SetDirectState(state)
        assert proxy.State() == state


def set_device_state(device, state, devFactory):
    proxy = devFactory.get_device(device)
    proxy.SetDirectState(state)
    assert proxy.State() == state

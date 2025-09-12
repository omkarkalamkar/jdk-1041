"""Settings file for test module"""

import json
import logging
import os
import time
from typing import List

import pytest
import tango
from ska_control_model import AdminMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_testing.mock.placeholders import Anything
from ska_tango_testing.mock.tango.event_callback import (
    MockTangoEventCallbackGroup,
)
from ska_tmc_common import FaultType, LivelinessProbeType
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)
from tests.mock_callable import MockCallable

logger = logging.getLogger(__name__)
TANGO_HOST = os.getenv("TANGO_HOST")
SLEEP_TIME = 0.5
TIMEOUT = 50
KVALUE = 9
DISH_LEAF_NODE_PREFIX = "mid-tmc/leaf-node-dish/ska"
NUM_DISHES = 10
LOW_CENTRAL_NODE = "low-tmc/central-node/0"
MID_CENTRAL_NODE = "mid-tmc/central-node/0"
MID_CSP_MLN_DEVICE = "mid-tmc/leaf-node-csp/0"
LOW_CSP_MLN_DEVICE = "low-tmc/leaf-node-csp/0"
MID_SDP_MLN_DEVICE = "mid-tmc/leaf-node-sdp/0"
LOW_SDP_MLN_DEVICE = "low-tmc/leaf-node-sdp/0"
MID_CSP_SLN_DEVICE = "mid-tmc/subarray-leaf-node-csp/01"
LOW_CSP_SLN_DEVICE = "low-tmc/subarray-leaf-node-csp/01"
MID_SDP_SLN_DEVICE = "mid-tmc/subarray-leaf-node-sdp/01"
LOW_SDP_SLN_DEVICE = "low-tmc/subarray-leaf-node-sdp/01"
MID_SUBARRAY_DEVICE = "mid-tmc/subarray/01"
LOW_SUBARRAY_DEVICE = "low-tmc/subarray/01"
DISH_LEAF_NODE_DEVICE = "mid-tmc/leaf-node-dish/ska001"
DISH_MASTER_DEVICE = "ska001/elt/master"
MID_SDP_MASTER_DEVICE = "mid-sdp/control/0"
MID_CSP_MASTER_DEVICE = "mid-csp/control/0"
LOW_CSP_MASTER_DEVICE = "low-csp/control/0"
LOW_SDP_MASTER_DEVICE = "low-sdp/control/0"
MCCS_CONTROLLER = "low-mccs/control/control"
MCCS_MLN_DEVICE = "low-tmc/leaf-node-mccs/0"
DEVICE_LIST_MID = [
    "mid-tmc/leaf-node-csp/0",
    "mid-csp/control/0",
    "mid-tmc/leaf-node-sdp/0",
    "mid-sdp/control/0",
    "mid-tmc/subarray/01",
    "mid-tmc/subarray-leaf-node-csp/01",
    "mid-tmc/subarray-leaf-node-sdp/01",
    "mid-tmc/leaf-node-dish/ska001",
    "ska001/elt/master",
]
DEVICE_LIST_LOW = [
    "low-tmc/leaf-node-mccs/0",
    "low-mccs/control/control",
    "low-tmc/subarray/01",
    "low-sdp/control/0",
    "low-csp/control/0",
    "low-tmc/leaf-node-csp/0",
    "low-tmc/leaf-node-sdp/0",
    "low-tmc/subarray-leaf-node-csp/01",
    "low-tmc/subarray-leaf-node-sdp/01",
]
TIMEOUT_DEFECT = json.dumps(
    {
        "enabled": True,
        "fault_type": FaultType.STUCK_IN_INTERMEDIATE_STATE,
        "error_message": "Command stuck in processing",
        "result": ResultCode.FAILED,
        "intermediate_state": ObsState.RESOURCING,
    }
)

ERROR_PROPAGATION_DEFECT = json.dumps(
    {
        "enabled": True,
        "fault_type": FaultType.LONG_RUNNING_EXCEPTION,
        "error_message": "Exception occurred, command failed.",
        "result": ResultCode.FAILED,
    }
)

DISH_DEFECT = json.dumps(
    {
        "enabled": True,
        "fault_type": FaultType.FAILED_RESULT,
        "error_message": "Error in calling command for dish devices",
        "result": ResultCode.FAILED,
    }
)


RESET_DEFECT = json.dumps(
    {
        "enabled": False,
        "fault_type": FaultType.FAILED_RESULT,
        "error_message": "Default exception.",
        "result": ResultCode.FAILED,
    }
)

CURRENT_TEST_DISH_VCC_KVALUE = 11


def set_devices_unresponsive(cm, device_names: list):
    """Sets devices unresponsive

    Args:
        cm: component manager instance
        device_names (list): devices names to be
        set as unresponsive
    """
    for device_name in device_names:
        dev_info = cm.get_device(device_name)
        dev_info.update_unresponsive(True, "Faulty")


def count_faulty_devices(cm):
    """Counts faulty devices"""
    result = 0
    for devInfo in cm.checked_devices:
        if devInfo.unresponsive:
            result += 1
    return result


def dish_vcc_process_callback(event):
    """Dummy dish vcc process callback for testing"""
    logger.debug("Dish Vcc process callback called with event %s", str(event))


def mock_update_device_callback(devInfo):
    """Dummy method for Update device callabacks"""
    logger.debug("Update device callabacks devInfo: %s", devInfo)


def mock_update_telescope_state_callback(telescope_state):
    """Dummy method for update telescope state callback"""
    logger.debug("telescope state: %s", str(telescope_state))


def mock_update_telescope_health_state_callback(telescope_health_state):
    """Dummy method for update telescope health state callback"""
    logger.debug("telescope health state: %s", str(telescope_health_state))


def mock_update_tmc_op_state_callback(tmc_op_state):
    """Dummy method for update tmc op state callback"""
    logger.debug("tmc op state: %s", str(tmc_op_state))


def mock_update_imaging_callback(imaging):
    """Callback for Update imaging"""
    logger.debug("imaging %s", str(imaging))


def mock_telescope_availability_callback(telescope_availability):
    """Dummy method for update telescope availability callback"""
    logger.debug("telescope availability: %s", str(telescope_availability))


def create_cm(
    p_liveliness_probe=False,
    p_event_manager=True,
    _input_parameter=InputParameterMid(None),
):
    """Creates component manager instance"""
    op_state_model = TMCOpStateModel(logger)

    # Creating component manager
    if isinstance(_input_parameter, InputParameterMid):
        unique_id = f"{time.time()}"
        task_callback = MockCallable(unique_id)
        cm = CNComponentManagerMid(
            op_state_model,
            _input_parameter=InputParameterMid(None),
            logger=logger,
            _dish_vcc_command_status_callback=dish_vcc_process_callback,
            _update_device_callback=mock_update_device_callback,
            _update_telescope_state_callback=(
                mock_update_telescope_state_callback
            ),
            _update_telescope_health_state_callback=(
                mock_update_telescope_health_state_callback
            ),
            _update_tmc_op_state_callback=(mock_update_tmc_op_state_callback),
            _update_imaging_callback=mock_update_imaging_callback,
            _telescope_availability_callback=(
                mock_telescope_availability_callback
            ),
            _update_dishvccconfig_callback=task_callback,
            _dishvccvalidation_callback=task_callback,
            _event_manager=p_event_manager,
            _liveliness_probe=LivelinessProbeType.NONE,
            enable_dish_vcc_init=False,
        )
        # In this unit test dish_vcc initialisation should not be run during
        # device
        # run because this unit test is explicitly calling load dish config
        # command.
        DEVICE_LIST = DEVICE_LIST_MID
        cm.is_dish_vcc_config_set = True
        cm.dish_vcc_command_status = DishConfigStatus.COMPLETED
    else:
        cm = CNComponentManagerLow(
            op_state_model,
            _input_parameter=InputParameterLow(None),
            logger=logger,
            _update_device_callback=mock_update_device_callback,
            _update_telescope_state_callback=(
                mock_update_telescope_state_callback
            ),
            _update_telescope_health_state_callback=(
                mock_update_telescope_health_state_callback
            ),
            _update_tmc_op_state_callback=(mock_update_tmc_op_state_callback),
            _update_imaging_callback=mock_update_imaging_callback,
            _telescope_availability_callback=(
                mock_telescope_availability_callback
            ),
            _event_manager=p_event_manager,
            _liveliness_probe=LivelinessProbeType.NONE,
        )
        DEVICE_LIST = DEVICE_LIST_LOW

    for dev in DEVICE_LIST:
        cm.add_device(dev)
    start_time = time.time()
    num_devices = len(DEVICE_LIST)
    if not p_liveliness_probe:
        cm.setup_event_subscription()
        return cm, start_time
    while num_devices != len(cm.checked_devices):
        time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    cm.setup_event_subscription()
    return cm, start_time


def create_cm_no_faulty_devices(
    tango_context,
    p_liveliness_probe,
    p_event_manager,
    _input_parameter=InputParameterMid(None),
):
    """creates component manager with no faulty devices"""
    logger.info("%s", tango_context)
    if isinstance(_input_parameter, InputParameterMid):
        _input_parameter = InputParameterMid(None)
        cm, start_time = create_cm(
            p_liveliness_probe, p_event_manager, _input_parameter
        )
        cm.is_dish_vcc_config_set = True
    else:
        _input_parameter = InputParameterLow(None)
        cm, start_time = create_cm(
            p_liveliness_probe, p_event_manager, _input_parameter
        )
    num_faulty = count_faulty_devices(cm)
    assert num_faulty == 0
    elapsed_time = time.time() - start_time
    logger.info("checked %d devices in %f", num_faulty, elapsed_time)
    return cm


def ensure_telescope_state(cm, state, expected_elapsed_time):
    """Checks telscope state"""
    start_time = time.time()
    elapsed_time = 0
    while cm.component.telescope_state != state:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            logger.error(
                "The current telescope state is %s",
                str(cm.component.telescope_state),
            )
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time


def ensure_tmc_op_state(cm, state, expected_elapsed_time):
    """Ensure tmc op state"""
    start_time = time.time()
    elapsed_time = 0
    while cm.component.tmc_op_state != state:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time


def ensure_imaging(cm, value, expected_elapsed_time):
    """Ensures imaging"""
    start_time = time.time()
    elapsed_time = 0
    while cm.component.imaging != value:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail("Timeout occurred while executing the test")
    assert elapsed_time < expected_elapsed_time


def set_devices_state(devices, state, devFactory):
    """Sets Devices state."""
    for device in devices:
        proxy = devFactory.get_device(device)
        proxy.SetDirectState(state)
        assert proxy.State() == state


def set_device_state(device, state, devFactory):
    """Sets device state"""
    proxy = devFactory.get_device(device)
    proxy.SetDirectState(state)
    assert proxy.State() == state


def set_dish_mode(device, dishmode, devFactory):
    """sets Dish mode"""
    proxy = devFactory.get_device(device)
    proxy.SetDirectDishMode(dishmode)
    assert proxy.dishmode == dishmode


def check_subarray_availability(central_node, subarray_fqdn, expected_status):
    """checks subarray availablity"""
    start_time = time.time()
    elapsed_time = 0
    while (json.loads(central_node.telescopeAvailability))["tmc_subarrays"][
        subarray_fqdn
    ] != expected_status:
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the SubarrayNode\
                      availability."
            )


def check_cspmln_availability(cm, expected_status):
    """checks cspmln availablity"""
    start_time = time.time()
    elapsed_time = 0
    while (
        cm.component.telescope_availability.get("csp_master_leaf_node")
        != expected_status
    ):
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the Csp Master Leaf Node."
                + " availability."
            )


def check_sdpmln_availability(cm, expected_status):
    """checks sdpmln availability"""
    start_time = time.time()
    elapsed_time = 0
    while (
        cm.component.telescope_availability.get("sdp_master_leaf_node")
        != expected_status
    ):
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the Sdp Master Leaf Node."
                + " availability."
            )


def check_mccsmln_availability(cm, expected_status):
    """checks mccs mln availability"""
    start_time = time.time()
    elapsed_time = 0
    while (
        cm.component.telescope_availability.get("mccs_master_leaf_node")
        != expected_status
    ):
        elapsed_time = time.time() - start_time
        time.sleep(0.1)
        if elapsed_time > TIMEOUT:
            pytest.fail(
                "Timeout occurred while checking the Mccs Master Leaf Node"
                + " availability."
            )


def event_remover(group_callback, attributes: List[str]) -> None:
    """Removes residual events from the queue."""
    for attribute in attributes:
        try:
            iterable = group_callback._mock_consumer_group._views[
                attribute
            ]._iterable
            for node in iterable:
                logger.info("Payload is: %s", repr(node.payload))
                node.drop()
        except KeyError:
            pass


def export_device(db, db_info):
    """Export device in database"""
    dev_export = tango.DbDevExportInfo()
    dev_export.name = db_info.name
    dev_export.ior = db_info.ior
    dev_export.host = TANGO_HOST
    dev_export.version = db_info.version
    dev_export.pid = db_info.pid

    db.export_device(dev_export)


def check_lrcr_events(
    change_event_callback: MockTangoEventCallbackGroup,
    command_name: str,
    result_to_check: ResultCode = ResultCode.OK,
    retries: int = 20,
):
    """Used to assert command name and result code in
       longRunningCommandResult event callbacks.

    Args:
        change_event_callback: MockTangoEventCallbackGroup
        command_name (str): command name to check
        result_code (ResultCode): result_code to check.
        Defaults to ResultCode.OK.
        retries (int):number of events to check. Defaults to 10.
    """
    COUNT = 0
    flag = False
    while not flag and COUNT <= retries:
        assertion_data = change_event_callback.assert_change_event(
            "longRunningCommandResult",
            Anything,
            lookahead=15,
        )
        unique_id, result = assertion_data["attribute_value"]
        if unique_id.endswith(command_name):
            if result == str(result_to_check):
                logger.debug("%s_UID: %s", command_name, unique_id)
                flag = True
        COUNT = COUNT + 1
        time.sleep(1)
    if flag:
        return True
    return False


def set_low_devices_availability():
    """Sets availability for low telescope."""
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    proxy_csp_mln.SetSubsystemAvailable(True)

    proxy_sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetSubsystemAvailable(True)

    proxy_mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
    proxy_mccs_mln.SetSubsystemAvailable(True)

    logging.debug(
        "CspSubarrayLeafNode availability is: %s",
        proxy_csp_mln.isSubsystemAvailable,
    )
    logging.debug(
        "SdpSubarrayLeafNode availability is: %s",
        proxy_sdp_mln.isSubsystemAvailable,
    )
    logging.debug(
        "MccsSubarrayLeafNode availability is: %s",
        proxy_mccs_mln.isSubsystemAvailable,
    )


def set_low_devices_admin_mode():
    """Sets Admin mode for low telescope."""
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    proxy_csp_mln.SetCspControllerAdminMode(AdminMode.ONLINE)

    proxy_sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetSdpControllerAdminMode(AdminMode.ONLINE)

    proxy_mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
    proxy_mccs_mln.SetMccsControllerAdminMode(AdminMode.ONLINE)
    logging.debug(
        "cspControllerAdminMode attrubte is: %s",
        proxy_csp_mln.cspControllerAdminMode,
    )
    logging.debug(
        "sdpControllerAdminMode attrubte is: %s",
        proxy_sdp_mln.sdpControllerAdminMode,
    )

    logging.debug(
        "mccsControllerAdminMode attrubte is: %s",
        proxy_mccs_mln.mccsControllerAdminMode,
    )


def set_auto_recovery_for_low(central_node_name: str, enabled: bool = True):
    """Sets the auto recovery property to True

    :param central_node_name: central node fqdn
    :type central_node_name: str
    """
    db = tango.Database()
    dev_factory = DevFactory()
    if (
        db.get_device_property(central_node_name, "IsAutoRecoveryEnabled")
        != enabled
    ):
        db.put_device_property(
            central_node_name, {"IsAutoRecoveryEnabled": enabled}
        )
        central_node = dev_factory.get_device(central_node_name)
        central_node.init()
        time.sleep(5)
        set_low_devices_admin_mode()
        set_low_devices_availability()

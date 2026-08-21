"""Settings file for test module"""

import json
import logging
import os
import threading
import time

import pytest
import tango
from ska_control_model import AdminMode
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.software_bus import _SignalBus
from ska_tango_testing.mock.placeholders import Anything
from ska_tango_testing.mock.tango.event_callback import (
    MockTangoEventCallbackGroup,
)
from ska_tmc_common import DishMode, FaultType, LivelinessProbeType
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.op_state_model import TMCOpStateModel

from ska_tmc_centralnode.manager.component_manager_config import (
    ArrayLayoutConfig,
    DishVccConfig,
    GPMConfig,
    LowCentralNodeComponentManagerConfig,
    MidCentralNodeComponentManagerConfig,
    TimeoutConfig,
)
from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.component import CentralComponent
from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)

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
MID_SUBARRAY2_DEVICE = "mid-tmc/subarray/02"
LOW_SUBARRAY_DEVICE = "low-tmc/subarray/01"
LOW_SUBARRAY2_DEVICE = "low-tmc/subarray/02"
DISH_LEAF_NODE_DEVICE = "mid-tmc/leaf-node-dish/ska001"
DISH_LEAF_NODE_DEVICE_099 = "mid-tmc/leaf-node-dish/ska099"
DISH_LEAF_NODE_DEVICE_500 = "mid-tmc/leaf-node-dish/ska500"
DISH_LEAF_NODE_DEVICE_999 = "mid-tmc/leaf-node-dish/ska999"

DISH_MASTER_DEVICE = "mid-dish/dish-manager/ska001"
DISH_MASTER_DEVICE_099 = "mid-dish/dish-manager/ska099"
DISH_MASTER_DEVICE_500 = "mid-dish/dish-manager/ska500"
DISH_MASTER_DEVICE_999 = "mid-dish/dish-manager/ska999"

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
    DISH_LEAF_NODE_DEVICE,
    DISH_LEAF_NODE_DEVICE_999,
    DISH_LEAF_NODE_DEVICE_500,
    DISH_LEAF_NODE_DEVICE_099,
    DISH_MASTER_DEVICE_099,
    DISH_MASTER_DEVICE,
    DISH_MASTER_DEVICE_500,
    DISH_MASTER_DEVICE_999,
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

CURRENT_TEST_DISH_VCC_KVALUE = 1

DISH_VCC_VALIDATION_RESULT_STATUS = {
    "dish": "ALL DISH OK",
}

TIMEOUT_MSG = "Timeout has occurred, command failed"
LOW_SUBARRAY_NOT_AVAILABLE = (
    "Subarray devices not available: ['low-tmc/subarray/01']"
)
MID_SUBARRAY_NOT_AVAILABLE = (
    "Subarray devices not available: ['mid-tmc/subarray/01']"
)


def telescope_on(
    central_node: tango.DeviceProxy,
    change_event_callbacks: MockTangoEventCallbackGroup,
) -> None:
    """Invokes telescope on"""
    result, unique_id = central_node.TelescopeOn()
    logger.info(
        "Telescope On Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )


def telescope_off(
    central_node: tango.DeviceProxy,
    change_event_callbacks: MockTangoEventCallbackGroup,
) -> None:
    """Invokes telescope off"""

    result, unique_id = central_node.TelescopeOff()
    logger.info(
        "AssignResources Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("TelescopeOff")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )


def clean_up_subarray(subarray: tango.DeviceProxy) -> None:
    """Cleans the mock subarray."""
    subarray.SetDefective(RESET_DEFECT)
    subarray.SetDirectObsState(ObsState.EMPTY)
    subarray.ClearCommandCallInfo()


def assign_resources(
    central_node: tango.DeviceProxy,
    assign_input_str: str,
    change_event_callbacks: MockTangoEventCallbackGroup,
):
    """Invoke assign reosurces command"""
    _, unique_id_assign = central_node.AssignResources(assign_input_str)
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            unique_id_assign[0],
            json.dumps((int(ResultCode.OK), "Command Completed")),
        ),
        lookahead=6,
    )


def check_exception(
    change_event_callbacks: MockTangoEventCallbackGroup,
    unique_id: tuple,
    device_name: str,
    exception_msg: str,
) -> None:
    """Checks the exception present in LRCR attribute."""
    event_data = change_event_callbacks[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=4,
    )

    assert exception_msg in event_data["attribute_value"][1]
    assert device_name in event_data["attribute_value"][1]


def check_dish_mode_event(
    dish_name: str,
    dish_mode: DishMode,
    change_event_callbacks: MockTangoEventCallbackGroup,
):
    """Checks the DishMode in the attribute event."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dish_name)
    evt_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["dishMode"],
    )

    change_event_callbacks["dishMode"].assert_change_event(
        dish_mode,
        lookahead=2,
    )
    dish_leaf_node.unsubscribe_event(evt_id)


def assert_exception(
    unique_id: tuple,
    exception_msg: str,
    change_event_callbacks: MockTangoEventCallbackGroup,
    result_code: ResultCode = ResultCode.FAILED,
):
    """Assert exceptions in LRCR attribute event."""
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            unique_id[0],
            json.dumps(
                (
                    int(result_code),
                    exception_msg,
                )
            ),
        ),
        lookahead=4,
    )


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
    for dev_info in cm.checked_devices:
        if dev_info.unresponsive:
            result += 1
    return result


def set_ldcfg_aggr_result(cm):
    """Temporary method to set dish vcc validation status for testing"""

    def set_load_dish_aggr_result(cm):
        with cm.command_completion_cond:
            cm.command_completion_cond.notify_all()

    threading.Timer(0.5, set_load_dish_aggr_result, args=[cm]).start()


def dish_vcc_process_callback(event):
    """Dummy dish vcc process callback for testing"""
    logger.debug("Dish Vcc process callback called with event %s", str(event))


def mock_update_device_callback(dev_info):
    """Dummy method for Update device callabacks"""
    logger.debug("Update device callabacks dev_info: %s", dev_info)


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


def invoke_set_gpm_command_callback():
    """Dummy method for invoke_set_gpm_command callback"""
    logger.debug("Invoked SetGlobalPointingCommand")


def array_layout_url_callback(url_dict):
    """Dummy method for array layout url callback"""
    logger.debug("Array layout URL callback: %s", url_dict)


def default_array_layout_url_callback(url_dict):
    """Dummy method for default array layout url callback"""
    logger.debug("Default array layout URL callback: %s", url_dict)


def _get_cm_mid_config(
    p_liveliness_probe=False,
    p_event_manager=True,
) -> MidCentralNodeComponentManagerConfig:
    default_array_layout_url_mid = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/"
            "ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": ("instrument/ska1_low/layout/low-layout.json"),
    }

    def cb(*_args, **_kwargs):
        pass

    bus_manager = BusManager()
    component = CentralComponent(logger)
    component.shared_bus = bus_manager.get_bus()
    config = MidCentralNodeComponentManagerConfig(
        component=component,
        op_state_model=TMCOpStateModel(logger),
        input_parameter=InputParameterMid(None),
        logger=logger,
        dish_config=DishVccConfig(
            uri="",
            file_path="",
            invoke_command_callback=cb,
            enable_init=False,
        ),
        gpm_config=GPMConfig(
            version="1.0.0",
            interface=(
                "https://schema.skao.int/ska-mid-global-pointing-model/1.0"
            ),
            data_sources_prefix=(
                "gitlab://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators"
            ),
            file_path_prefix=(
                "instrument/ska_mid1/global_pointing_model_data"
            ),
            invoke_command_callback=invoke_set_gpm_command_callback,
        ),
        timeout_config=TimeoutConfig(),
        array_layout_config=ArrayLayoutConfig(
            default_url=default_array_layout_url_mid
        ),
        subarray_trl_prefix="mid-tmc/subarray/",
        mkt_extension_id="",
    )
    if not p_liveliness_probe:
        config.liveliness_probe_type = LivelinessProbeType.NONE
    config.event_manager_enabled = p_event_manager
    return config


def _get_cm_low_config(
    p_liveliness_probe=False,
    p_event_manager=True,
) -> LowCentralNodeComponentManagerConfig:
    default_array_layout_url_low = {
        "source_uris": [
            "gitlab://gitlab.com/ska-telescope/"
            "ska-telmodel-data?main#tmdata"
        ],
        "array_layout_path": ("instrument/ska1_low/layout/low-layout.json"),
    }
    bus_manager = BusManager()
    component = CentralComponent(logger)
    component.shared_bus = bus_manager.get_bus()
    config = LowCentralNodeComponentManagerConfig(
        component=component,
        op_state_model=TMCOpStateModel(logger),
        input_parameter=InputParameterLow(None),
        logger=logger,
        timeout_config=TimeoutConfig,
        array_layout_config=ArrayLayoutConfig(
            default_url=default_array_layout_url_low
        ),
        subarray_trl_prefix="low-tmc/subarray/",
        is_auto_recovery_enabled=True,
    )
    if not p_liveliness_probe:
        config.liveliness_probe_type = LivelinessProbeType.NONE
    config.event_manager_enabled = p_event_manager
    return config


class BusManager:
    """Class to manage signal bus."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.bus = _SignalBus()

    def get_bus(self):
        """Provides signal bus."""
        return self.bus

    # pylint:disable=protected-access
    def start_bus(self):
        """Starts the signal bus for testing."""
        if self.bus._thread.is_alive():
            self.bus.shutdown_thread()
        self.bus.start_thread()

    # pylint:enable=protected-access


def create_cm(
    p_liveliness_probe=False,
    p_event_manager=True,
    _input_parameter=InputParameterMid(None),
):
    """Creates component manager instance"""
    # Creating component manager
    bus_manager = BusManager()
    bus_manager.start_bus()
    if isinstance(_input_parameter, InputParameterMid):
        cm = CNComponentManagerMid(
            config=_get_cm_mid_config(p_liveliness_probe, p_event_manager)
        )
        # In this unit test dish_vcc initialisation should not be run during
        # device
        # run because this unit test is explicitly calling load dish config
        # command.
        device_list = DEVICE_LIST_MID
        cm.component.shared_bus = bus_manager.get_bus()
        cm.shared_bus = bus_manager.get_bus()
        cm.is_dish_vcc_config_set = True
        cm.dish_vcc_command_status = DishConfigStatus.COMPLETED
    else:
        cm = CNComponentManagerLow(
            config=_get_cm_low_config(p_liveliness_probe, p_event_manager)
        )
        device_list = DEVICE_LIST_LOW
        cm.component.shared_bus = bus_manager.get_bus()
        cm.shared_bus = bus_manager.get_bus()
    for dev in device_list:
        cm.add_device(dev)
    start_time = time.time()
    num_devices = len(device_list)
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
    logger.debug("Tango context: %s", tango_context)
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


def set_devices_state(devices, state, dev_factory):
    """Sets Devices state."""
    for device in devices:
        proxy = dev_factory.get_device(device)
        proxy.SetDirectState(state)
        assert proxy.State() == state


def set_device_state(device, state, dev_factory):
    """Sets device state"""
    proxy = dev_factory.get_device(device)
    proxy.SetDirectState(state)
    assert proxy.State() == state


def set_dish_mode(device, dishmode, dev_factory):
    """sets Dish mode"""
    proxy = dev_factory.get_device(device)
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
    result_to_check: str = '[0,"Command Completed"]',
    retries: int = 20,
    callback_name: str = "longRunningCommandResult",
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
    count = 0
    flag = False
    while not flag and count <= retries:
        assertion_data = change_event_callback[
            callback_name
        ].assert_change_event(
            Anything,
            lookahead=15,
        )
        unique_id, result = assertion_data["attribute_value"]
        info_string = json.loads(result_to_check)
        received_result = json.loads(result)
        if unique_id.endswith(command_name):
            if (
                received_result[0] == info_string[0]
                and info_string[1] in received_result[1]
            ):
                logger.debug("%s_UID: %s", command_name, unique_id)
                flag = True
        count = count + 1
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


def set_low_devices_admin_mode():
    """Sets Admin mode for low telescope."""
    dev_factory = DevFactory()
    proxy_csp_mln = dev_factory.get_device(LOW_CSP_MLN_DEVICE)
    proxy_csp_mln.SetCspControllerAdminMode(AdminMode.ONLINE)

    proxy_sdp_mln = dev_factory.get_device(LOW_SDP_MLN_DEVICE)
    proxy_sdp_mln.SetSdpControllerAdminMode(AdminMode.ONLINE)

    proxy_mccs_mln = dev_factory.get_device(MCCS_MLN_DEVICE)
    proxy_mccs_mln.SetMccsControllerAdminMode(AdminMode.ONLINE)


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

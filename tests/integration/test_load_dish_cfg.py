"""Test cases for Load_Dish_Config command"""

import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DeviceProxy

from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.utils.constants import CENTRALNODE_MID
from tests.common_utils import (
    is_device_ready,
    wait_and_validate_device_attribute_value,
)
from tests.integration.conftest import ensure_checked_devices
from tests.settings import (
    CURRENT_TEST_DISH_VCC_KVALUE,
    DISH_LEAF_NODE_DEVICE,
    ERROR_PROPAGATION_DEFECT,
    MID_CSP_MLN_DEVICE,
    RESET_DEFECT,
    check_lrcr_events,
    logger,
)


def validate_attribute_after_restart(
    csp_mln: DeviceProxy, dish_cfg_str: str
) -> None:
    """Restart csp mln and validate memorized attribute"""
    # Restart the csp master leaf node
    csp_mln.init()
    assert is_device_ready(
        MID_CSP_MLN_DEVICE, "sourceDishVccConfig"
    ), f"{MID_CSP_MLN_DEVICE} is not Started after restart"
    assert json.loads(csp_mln.memorizedDishVccMap) == json.loads(dish_cfg_str)


def load_dish_cfg(central_node_name, config_str, change_event_callbacks):
    """Test cases for Load_Dish_Config command"""
    logger.info("%s", config_str)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    dish_ln_device = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)

    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    central_node.subscribe_event(
        "DishVccCommandStatus",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["DishVccCommandStatus"],
    )

    result, unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        "LoadDishCfg Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED
    change_event_callbacks["DishVccCommandStatus"].assert_change_event(
        DishConfigStatus.IN_PROGRESS,
        lookahead=4,
    )

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    change_event_callbacks["DishVccCommandStatus"].assert_change_event(
        DishConfigStatus.COMPLETED,
        lookahead=4,
    )

    # Validate dishVccConfigs are set on Csp Master Device
    assert json.loads(csp_master_ln_device.sourceDishVccConfig) == json.loads(
        config_str
    )
    # Validate kValue is set on dish
    assert dish_ln_device.kValue == CURRENT_TEST_DISH_VCC_KVALUE

    assert json.loads(csp_master_ln_device.memorizedDishVccMap) == json.loads(
        config_str
    )

    # Validate when csp mln restart memorizedDishVccMap remains same
    validate_attribute_after_restart(
        csp_master_ln_device,
        config_str,
    )


def invoke_load_dish_config(
    central_node_name,
    config_str,
    change_event_callbacks,
):
    """Invoke LoadDishCfg with correct Dish VCC
    map path to recover from failed state."""

    logger.info("Invoking LoadDishCfg with correct VCC map path...")

    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    dish_ln_device = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)

    ensure_checked_devices(central_node)

    # Correct path for tm_data_sources
    dish_cfg_input = json.loads(config_str)
    dish_cfg_input.update(
        {
            "tm_data_sources": [
                # correct SKA CAR
                "car://gitlab.com/ska-telescope/ska-tmc/"
                "ska-tmc-simulators?main#tmdata"
            ]
        }
    )

    # Subscribe to events
    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    central_node.subscribe_event(
        "DishVccCommandStatus",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["DishVccCommandStatus"],
    )

    # Run the command
    result, unique_id = central_node.LoadDishCfg(json.dumps(dish_cfg_input))
    logger.info(
        "Reattempted LoadDishCfg Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    # Command should queue
    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED

    # Validate sequence of events
    change_event_callbacks["DishVccCommandStatus"].assert_change_event(
        DishConfigStatus.IN_PROGRESS,
        lookahead=4,
    )

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )

    change_event_callbacks["DishVccCommandStatus"].assert_change_event(
        DishConfigStatus.COMPLETED,
        lookahead=4,
    )

    # Ensure CSP and Dish configs are applied correctly
    assert json.loads(csp_master_ln_device.sourceDishVccConfig) == json.loads(
        json.dumps(dish_cfg_input)
    )
    assert dish_ln_device.kValue == CURRENT_TEST_DISH_VCC_KVALUE
    assert json.loads(csp_master_ln_device.memorizedDishVccMap) == json.loads(
        json.dumps(dish_cfg_input)
    )

    # Persist config across restarts
    validate_attribute_after_restart(
        csp_master_ln_device,
        json.dumps(dish_cfg_input),
    )

    logger.info("Successfully reloaded Dish VCC configuration.")


def load_dish_cfg_rejected(
    central_node_name, config_str, change_event_callbacks
):
    """Test LoadDishCfg rejected when existing
    LoadDishCfg command is in progress"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)

    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    central_node.subscribe_event(
        "DishVccCommandStatus",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["DishVccCommandStatus"],
    )
    # Set delay for load dish cfg command
    csp_master_ln_device.SetDelay(5)
    result, unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        "LoadDishCfg Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED
    change_event_callbacks["DishVccCommandStatus"].assert_change_event(
        DishConfigStatus.IN_PROGRESS,
        lookahead=4,
    )
    # Invoke Another LoadDishCfg command
    second_result, second_unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        "second LoadDishCfg Command ID: %s Returned result %s",
        second_unique_id,
        second_result,
    )
    assert second_result[0] == ResultCode.QUEUED
    message = (
        "Dish Vcc Configuration is in Progress. "
        "Dish Vcc command status: %s ",
        str(DishConfigStatus.IN_PROGRESS),
    )
    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (
            second_unique_id[0],
            json.dumps(
                (
                    int(ResultCode.NOT_ALLOWED),
                    message,
                )
            ),
        ),
        lookahead=4,
    )

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=4,
    )
    change_event_callbacks["DishVccCommandStatus"].assert_change_event(
        DishConfigStatus.COMPLETED,
        lookahead=8,
    )
    csp_master_ln_device.SetDelay(2)


def load_dish_cfg_when_csp_is_defective(
    central_node_name,
    config_str,
    change_event_callbacks,
):
    """Test cases for Load_Dish_Config command with csp defective"""
    logger.info("%s", config_str)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    csp_master_ln_device.SetDefective(ERROR_PROPAGATION_DEFECT)
    ensure_checked_devices(central_node)

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    result, unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        "LoadDishCfg Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED

    expected_failed_message = (
        f'[{ResultCode.FAILED}, "Exception occurred on the following devices: '
        f'{MID_CSP_MLN_DEVICE}: Exception occurred, command failed."]'
    )
    logger.info(f"{expected_failed_message} is this")

    assert check_lrcr_events(
        change_event_callback=change_event_callbacks,
        command_name="LoadDishCfg",
        result_to_check=expected_failed_message,
    )

    assert central_node.telescopeState == tango.DevState.UNKNOWN

    csp_master_ln_device.SetDefective(RESET_DEFECT)

    result, unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        "LoadDishCfg Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    change_event_callbacks["longRunningCommandResult"].assert_change_event(
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=8,
    )


def load_dish_cfg_after_central_node_init(
    central_node_name, config_str, change_event_callbacks
):
    """Test cases for Load_Dish_Config command"""
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    dish_ln_device = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    # Central Node and Csp Master Leaf Node Device Server
    central_node_ds = DeviceProxy("dserver/central_node_mid/01")
    csp_master_ln_ds = DeviceProxy("dserver/mocks/01")
    dish_ln_ds = DeviceProxy("dserver/mocks/07")
    # set memorized attribute to empty
    csp_master_ln_device.memorizedDishVccMap = ""

    # Restart Central Node, CSP Master Leaf Node, Dish Leaf Node
    csp_master_ln_ds.RestartServer()
    dish_ln_ds.RestartServer()
    assert wait_and_validate_device_attribute_value(
        dish_ln_device, "State", tango.DevState.ON
    )
    assert wait_and_validate_device_attribute_value(
        csp_master_ln_device, "State", tango.DevState.ON
    )

    central_node_ds.RestartServer()
    assert wait_and_validate_device_attribute_value(
        central_node, "State", tango.DevState.ON
    )

    # Validate LoadDishCfg command called after initialization

    central_node.subscribe_event(
        "isDishVccConfigSet",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["isDishVccConfigSet"],
    )
    assert wait_and_validate_device_attribute_value(
        central_node, "isDishVccConfigSet", False
    ), "Timeout while waiting for validating attribute value"

    change_event_callbacks["isDishVccConfigSet"].assert_change_event(
        (False),
        lookahead=4,
    )

    assert wait_and_validate_device_attribute_value(
        central_node, "isDishVccConfigSet", True
    ), "Timeout while waiting for validating attribute value"

    change_event_callbacks["isDishVccConfigSet"].assert_change_event(
        True,
        lookahead=4,
    )

    assert wait_and_validate_device_attribute_value(
        csp_master_ln_device, "memorizedDishVccMap", config_str, is_json=True
    )


def central_node_dish_vcc_after_csp_master_dish_ln_restart(
    central_node_name, config_str, change_event_callbacks
):
    """Validate When only CSP master leaf node and dish leaf node restart
    then Central Node update it's dishVccValidationResult properly
    """
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    dish_ln_device = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    csp_master_ln_device.subscribe_event(
        "DishVccMapValidationResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["DishVccMapValidationResult"],
    )
    # Csp Master Leaf Node and Dish Leaf Node Device Server
    csp_master_ln_ds = DeviceProxy("dserver/mocks/01")
    dish_ln_ds = DeviceProxy("dserver/mocks/07")
    # Validate before restart memorizedDishVccMap is set
    assert json.loads(csp_master_ln_device.memorizedDishVccMap) == json.loads(
        config_str
    )

    # Restart CSP Master Leaf Node, Dish Leaf Node
    csp_master_ln_ds.RestartServer()
    dish_ln_ds.RestartServer()
    assert wait_and_validate_device_attribute_value(
        dish_ln_device, "State", tango.DevState.ON
    )
    assert wait_and_validate_device_attribute_value(
        csp_master_ln_device, "State", tango.DevState.ON
    )

    # Validate DishVccValidationResult return OK
    change_event_callbacks["DishVccMapValidationResult"].assert_change_event(
        str(int(ResultCode.OK)),
        lookahead=4,
    )

    assert wait_and_validate_device_attribute_value(
        dish_ln_device, "kValueValidationResult", str(int(ResultCode.OK))
    ), "Timeout while waiting for validating attribute value"

    assert wait_and_validate_device_attribute_value(
        central_node, "isDishVccConfigSet", True
    ), "Timeout while waiting for validating attribute value"


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_load_dish_cfg(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command"""
    return load_dish_cfg(
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_load_dish_cfg_rejected(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test LoadDishCfg command rejected
    when existing command is in progress
    """
    return load_dish_cfg_rejected(
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_load_dish_cfg_when_csp_is_defective(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command"""
    return load_dish_cfg_when_csp_is_defective(
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.restart_device_server
@pytest.mark.post_deployment
@pytest.mark.xfail(
    reason="Intermittentent failure due to device server restart"
)
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_load_dish_cfg_after_central_node_init(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command after central node
    initialisation"""
    return load_dish_cfg_after_central_node_init(
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.xfail(
    reason="Intermittentent failure due to device server restart"
)
@pytest.mark.post_deployment
@pytest.mark.restart_device_server
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_central_node_dish_vcc_after_csp_master_dish_ln_restart(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command after csp master dish Leaf node
    restarts"""
    return central_node_dish_vcc_after_csp_master_dish_ln_restart(
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


def load_dish_cfg_with_wrong_path(
    central_node_name,
    config_str,
    change_event_callbacks,
    json_factory=None,
):
    """Test cases for Load_Dish_Config command with csp defective"""
    logger.info("%s", config_str)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    ensure_checked_devices(central_node)

    dish_cfg_input = json.loads(config_str)
    dish_cfg_input.update(
        {
            "tm_data_sources": [
                "car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simulators?t1#tmdata"
            ]
        }
    )

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )
    result, unique_id = central_node.LoadDishCfg(json.dumps(dish_cfg_input))
    logger.info(
        "LoadDishCfg Command ID: %s Returned result: %s",
        unique_id,
        str(result),
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED

    expected_failed_message = json.dumps(
        [
            ResultCode.FAILED,
            "Error in Loading"
            + " Dish VCC map json file gitlab://gitlab.com/ska-telescope/ska-tmc/ska-"
            + "tmc-simulators?t1#tmdata not found in SKA CAR - make sure to add "
            + "tmdata CI!",
        ]
    )
    logger.info(f"{expected_failed_message} is this")

    assert check_lrcr_events(
        change_event_callback=change_event_callbacks,
        command_name="LoadDishCfg",
        result_to_check=expected_failed_message,
    )

    assert central_node.telescopeState == tango.DevState.UNKNOWN

    # Recover by loading the correct Dish VCC config
    invoke_load_dish_config(
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [CENTRALNODE_MID],
)
def test_load_dish_cfg_with_wrong_path(
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command"""
    return load_dish_cfg_with_wrong_path(
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
        json_factory,
    )

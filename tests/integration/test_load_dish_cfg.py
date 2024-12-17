"""Test cases for Load_Dish_Config command"""
import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DeviceProxy

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
    event_remover,
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


def load_dish_cfg(
    tango_context, central_node_name, config_str, change_event_callbacks
):
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

    result, unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        "LoadDishCfg Command ID: %s Returned result: %s",
        unique_id,
        result,
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
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

    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult"],
    )


def load_dish_cfg_when_csp_is_defective(
    tango_context,
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
        result,
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED

    expected_failed_message = (
        f'[{ResultCode.FAILED}, "Exception occurred on device: '
        f'Command failed on device {MID_CSP_MLN_DEVICE}: Exception occurred, command failed."]'
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
        result,
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], json.dumps((int(ResultCode.OK), "Command Completed"))),
        lookahead=8,
    )

    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult"],
    )


def load_dish_cfg_after_central_node_init(
    tango_context, central_node_name, config_str, change_event_callbacks
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

    change_event_callbacks.assert_change_event(
        "isDishVccConfigSet",
        (False),
        lookahead=4,
    )

    assert wait_and_validate_device_attribute_value(
        central_node, "isDishVccConfigSet", True
    ), "Timeout while waiting for validating attribute value"

    change_event_callbacks.assert_change_event(
        "isDishVccConfigSet",
        True,
        lookahead=4,
    )

    assert wait_and_validate_device_attribute_value(
        csp_master_ln_device, "memorizedDishVccMap", config_str, is_json=True
    )


def central_node_dish_vcc_after_csp_master_dish_ln_restart(
    tango_context, central_node_name, config_str, change_event_callbacks
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
    change_event_callbacks.assert_change_event(
        "DishVccMapValidationResult",
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
@pytest.mark.SKA_midm
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_load_dish_cfg(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command"""
    return load_dish_cfg(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_midm
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_load_dish_cfg_when_csp_is_defective(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command"""
    return load_dish_cfg_when_csp_is_defective(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


# Test Cases with with requirment to restart server fail
# randomly due to issues in restart
@pytest.mark.skip(
    reason="Skipped due to intermittent failures "
    ", Raised SKB-404 to track same"
)
@pytest.mark.post_deployment
@pytest.mark.SKA_midm
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_load_dish_cfg_after_central_node_init(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command after central node
    initialisation"""
    return load_dish_cfg_after_central_node_init(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.skip(reason="Fails intermittently")
@pytest.mark.post_deployment
@pytest.mark.SKA_midm
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_central_node_dish_vcc_after_csp_master_dish_ln_restart(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command after csp master dish Leaf node
    restarts"""
    return central_node_dish_vcc_after_csp_master_dish_ln_restart(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


def load_dish_cfg_with_wrong_path(
    tango_context,
    central_node_name,
    config_str,
    change_event_callbacks,
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
        result,
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

    event_remover(
        change_event_callbacks,
        ["longRunningCommandResult"],
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_midm
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_load_dish_cfg_with_wrong_path(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    """Test cases for Load_Dish_Config command"""
    return load_dish_cfg_with_wrong_path(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )

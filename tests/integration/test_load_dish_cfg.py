import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from tango import DeviceProxy

from tests.common_utils import is_device_ready, tear_down
from tests.integration.conftest import (
    CURRENT_TEST_DISH_VCC_KVALUE,
    ensure_checked_devices,
)
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    ERROR_PROPAGATION_DEFECT,
    MID_CSP_MLN_DEVICE,
    RESET_DEFECT,
    logger,
)


def validate_attribute_after_restart(csp_mln, dish_cfg_str):
    """Restart csp mln and validate memorized attribute"""
    # Restart the csp master leaf node
    csp_mln_device = DeviceProxy("dserver/mocks/01")
    csp_mln_device.Kill()
    assert is_device_ready(
        MID_CSP_MLN_DEVICE, "sourceDishVccConfig"
    ), f"{MID_CSP_MLN_DEVICE} is not Started after restart"
    assert json.loads(csp_mln.memorizedDishVccMap) == json.loads(dish_cfg_str)


def load_dish_cfg(
    tango_context,
    central_node_name,
    config_str,
    change_event_callbacks,
    test_csp_mln_restart=False,
):
    logger.info("%s", config_str)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    dish_ln_device = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=5,
    )

    result, unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        f"LoadDishCfg Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=7,
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

    if test_csp_mln_restart:
        # Validate when csp mln restart memorizedDishVccMap remains same
        validate_attribute_after_restart(csp_master_ln_device, config_str)

    ensure_checked_devices(central_node)

    tear_down(central_node_name, reset_sys_param=True)


def load_dish_cfg_when_csp_is_defective(
    tango_context,
    central_node_name,
    config_str,
    change_event_callbacks,
):
    logger.info("%s", config_str)
    dev_factory = DevFactory()
    central_node = dev_factory.get_device(central_node_name)
    csp_master_ln_device = dev_factory.get_device(MID_CSP_MLN_DEVICE)

    ensure_checked_devices(central_node)

    result, unique_id = central_node.TelescopeOn()
    logger.info(
        f"TelescopeOn Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("TelescopeOn")
    assert result[0] == ResultCode.QUEUED

    central_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        change_event_callbacks["longRunningCommandResult"],
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], str(int(ResultCode.OK))),
        lookahead=5,
    )

    csp_master_ln_device.SetDefective(ERROR_PROPAGATION_DEFECT)

    result, unique_id = central_node.LoadDishCfg(config_str)
    logger.info(
        f"LoadDishCfg Command ID: {unique_id} Returned result: {result}"
    )

    assert unique_id[0].endswith("LoadDishCfg")
    assert result[0] == ResultCode.QUEUED

    EXPECTED_FAILED_MESSAGE = (
        f"Exception occurred on device:"
        f" Command failed on device {MID_CSP_MLN_DEVICE}: "
        "Exception occurred, command failed."
    )

    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (unique_id[0], EXPECTED_FAILED_MESSAGE),
        lookahead=8,
    )

    csp_master_ln_device.SetDefective(RESET_DEFECT)

    tear_down(central_node_name, reset_sys_param=True)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
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
    return load_dish_cfg(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
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
    return load_dish_cfg_when_csp_is_defective(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "central_node_name",
    [("ska_mid/tm_central/central_node")],
)
def test_memorized_dish_vcc_map_version(
    tango_context,
    central_node_name,
    change_event_callbacks,
    json_factory,
):
    return load_dish_cfg(
        tango_context,
        central_node_name,
        json_factory("command_load_dish_cfg"),
        change_event_callbacks,
        test_csp_mln_restart=True,
    )

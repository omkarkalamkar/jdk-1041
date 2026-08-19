"""Test module for command load dish cfg"""
import json
import threading
from unittest.mock import MagicMock, patch

import mock
import pytest
import tango
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)
from tango import ApiUtil

from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.refactored_commands.load_dish_cfg.errors import (
    DishAdapterError,
)
from ska_tmc_centralnode.refactored_commands.load_dish_cfg.load_dish_config_command import (
    LoadDishCfg,
)
from ska_tmc_centralnode.utils.json_validator_decorator import (
    validate_dish_vcc_command_status,
)
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    MID_CSP_MLN_DEVICE,
    create_cm,
    logger,
    set_ldcfg_aggr_result,
)

# Helper Dish LN device is using Database API and in Unit test Database API
# is not callable
# Patch this particular method which mock return value from SetKValue command


@patch.object(LoadDishCfg, "_execute_on_dish")
def test_load_dish_cfg_command(
    execute_on_dish,
    tango_context,
    task_callback,
    json_factory,
):
    """Test load dish cfg invoke on devices with task status as completed"""
    # This need to be set to enable async command callback event
    ApiUtil.instance().set_asynch_cb_sub_model(
        tango.cb_sub_model.PUSH_CALLBACK
    )
    cm, _ = create_cm()
    cm.is_csp_mln_csp_master_ready = mock.MagicMock(return_value=ResultCode.OK)
    dln = tango.DeviceProxy("mid-tmc/leaf-node-dish/ska001")
    execute_on_dish.return_value = ([ResultCode.QUEUED], [""])
    dln.SetDirectkValueValidationResult("0")
    cm.is_dish_vcc_config_set = True
    dish_cfg_input_str = json_factory("command_load_dish_cfg")
    set_ldcfg_aggr_result(cm)
    with mock.patch.object(
        cm.dish_kvalue_validation_aggregator,
        "dln_kvalue_validation_results",
        {"ska001": "k-value identical"},
    ):
        cm._event_cb_manager.update_k_value_validation(
            DISH_LEAF_NODE_DEVICE, ResultCode.OK
        )
        cm.load_dish_cfg(
            dish_cfg_input_str,
            task_callback=task_callback,
            task_abort_event=threading.Event(),
        )
        task_callback.assert_against_call(
            call_kwargs={"status": TaskStatus.IN_PROGRESS}
        )
        task_callback.assert_against_call(
            call_kwargs={
                "status": TaskStatus.COMPLETED,
                "result": (ResultCode.OK, "Command Completed"),
            },
            lookahead=20,
        )

    assert cm.dish_vcc_command_status == DishConfigStatus.COMPLETED
    # Validate memorizedDishVccMap attribute set
    dev_factory = DevFactory()
    csp_mln = dev_factory.get_device(MID_CSP_MLN_DEVICE)
    assert csp_mln.memorizedDishVccMap == dish_cfg_input_str


def test_load_dish_cfg_command_invalid_json(
    tango_context, task_callback, json_factory, set_mid_sdp_csp_admin_modes
):
    """Test LoadDishCfg command rejected when invalid json provided"""
    cm, _ = create_cm()
    cm.is_csp_mln_csp_master_ready = mock.MagicMock(return_value=ResultCode.OK)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg")

    dish_cfg_input = json.loads(dish_cfg_input_str)
    dish_cfg_input.pop("tm_data_sources")

    cm.load_dish_cfg(
        json.dumps(dish_cfg_input),
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    assertion_data = task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.FAILED,
                Anything,
            ),
            "exception": Anything,
        },
    )
    err_message = (
        "tm_data_sources and tm_data_filepath not provided"
        " in json LoadDishCfg command failed"
    )
    assert err_message in assertion_data["call_kwargs"]["result"][1]
    assert err_message in assertion_data["call_kwargs"]["exception"]
    logger.info("Assertion data: %s", assertion_data)


def test_load_dish_cfg_command_kvalue_out_of_range(
    tango_context, task_callback, json_factory, set_mid_sdp_csp_admin_modes
):
    """Test LoadDishCfg command rejected when kvalue is out of range"""
    cm, _ = create_cm()
    cm.is_csp_mln_csp_master_ready = mock.MagicMock(return_value=ResultCode.OK)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("load_dish_cfg_kvalue_out_of_range")
    cm.load_dish_cfg(
        dish_cfg_input_str,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    exception_message = "K values are not in range (1 to 1177)"
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    assertion_data = task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.FAILED,
                Anything,
            ),
            "exception": Anything,
        },
    )
    assert exception_message in assertion_data["call_kwargs"]["result"][1]
    assert exception_message in assertion_data["call_kwargs"]["exception"]


def test_load_dish_cfg_command_invalid_file_name(
    tango_context, task_callback, json_factory, set_mid_sdp_csp_admin_modes
):
    """Test LoadDishCfg command rejected when invalid json provided"""
    cm, _ = create_cm()
    cm.is_csp_mln_csp_master_ready = mock.MagicMock(return_value=ResultCode.OK)
    cm.is_dish_vcc_config_set = True
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg_invalid")

    dish_cfg_input = json.loads(dish_cfg_input_str)

    cm.load_dish_cfg(
        json.dumps(dish_cfg_input),
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    err_message = (
        "Error in Loading Dish VCC map json file"
        " 'No telescope model data with key"
    )
    assertion_data = task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.FAILED,
                Anything,
            ),
            "exception": Anything,
        },
    )
    assert err_message in assertion_data["call_kwargs"]["result"][1]
    assert err_message in assertion_data["call_kwargs"]["exception"]


def test_dish_vcc_validation_status(task_callback, json_factory):
    """Test dish vcc validation result of component manager"""

    cm, _ = create_cm()
    cm.dish_vcc_command_status = DishConfigStatus.STAGING
    cm._event_cb_manager.handle_dish_vcc_validation_result(
        MID_CSP_MLN_DEVICE, ResultCode.OK
    )
    assert cm.dish_vcc_command_status == DishConfigStatus.COMPLETED
    assert json.loads(cm.dish_vcc_validation_status) == {
        "mid-tmc/leaf-node-csp/0": "TMC and CSP Master Dish Vcc Version is Same"
    }

    cm._event_cb_manager.handle_dish_vcc_validation_result(
        MID_CSP_MLN_DEVICE, ResultCode.FAILED
    )
    assert json.loads(cm.dish_vcc_validation_status) == {
        "mid-tmc/leaf-node-csp/0": "TMC and CSP Master Dish VCC version is Different"
    }

    cm._event_cb_manager.handle_dish_vcc_validation_result(
        MID_CSP_MLN_DEVICE, ResultCode.NOT_ALLOWED
    )
    assert json.loads(cm.dish_vcc_validation_status) == {
        "mid-tmc/leaf-node-csp/0": "CSP Master device is unavailable"
    }
    # Validate Dish Config status flag
    cm.check_if_csp_all_dish_ready = mock.Mock()
    cm.check_if_csp_all_dish_ready.return_value = True
    cm.config.dish_config.invoke_command_callback = mock.Mock()
    cm._event_cb_manager.check_if_csp_all_dish_ready = mock.Mock()

    cm._event_cb_manager.handle_dish_vcc_validation_result(
        MID_CSP_MLN_DEVICE, ResultCode.UNKNOWN
    )
    assert cm.dish_vcc_command_status == DishConfigStatus.INIT

    cm._event_cb_manager.check_if_csp_all_dish_ready.return_value = False
    cm.command_in_progress = ""
    cm._event_cb_manager.handle_dish_vcc_validation_result(
        MID_CSP_MLN_DEVICE, ResultCode.UNKNOWN
    )
    assert cm.dish_vcc_command_status == DishConfigStatus.FAILED


def test_load_dish_cnfg_command_fail_csp_master(
    tango_context, json_factory, set_mid_sdp_csp_admin_modes
):
    cm, _ = create_cm()
    adapter_factory = HelperAdapterFactory()
    sub_mock = mock.Mock(
        **{"invoke_command.side_effect": Exception("command failed")}
    )
    adapter_factory.get_or_create_adapter(MID_CSP_MLN_DEVICE, proxy=sub_mock)
    dish_cfg_input_str = json_factory("command_load_dish_cfg")
    load_dish_cnfg_command = LoadDishCfg(
        cm._get_load_dish_cfg_context(), adapter_factory, logger=logger
    )
    # (
    #     load_dish_cnfg_command.dish_vcc_config_json,
    #     _,
    # ) = load_dish_cnfg_command.check_and_validate_dish_vcc_data(
    #     dish_cfg_input_str
    # )
    (res_code, _) = load_dish_cnfg_command.execute(
        dish_cfg_input_str,
        task_callback=mock.Mock(),
        task_abort_event=mock.Mock(),
    )
    assert res_code == ResultCode.FAILED


def test_load_dish_config_command_fail(
    tango_context, json_factory, task_callback, set_mid_sdp_csp_admin_modes
):
    # Validate load dish cfg is rejected if dish vcc process status
    # is in progress
    cm, _ = create_cm()
    cm.dish_vcc_command_status = DishConfigStatus.IN_PROGRESS
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg_invalid")

    dish_cfg_input = json.loads(dish_cfg_input_str)
    decorated = validate_dish_vcc_command_status(cm.load_dish_cfg)

    result_code, message = decorated(cm, json.dumps(dish_cfg_input))

    assert result_code == [ResultCode.REJECTED]
    assert (
        message[0]
        == "Dish Vcc Configuration is in Progress. Dish Vcc command status: IN_PROGRESS"
    )


# ---------------------------------------------------------------------------
# get_dish_adapters
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "device_states, adapter_side_effect, expected_names, expected_calls",
    [
        pytest.param(
            # All devices are responsive and adapters are created.
            [False, False],
            [
                MagicMock(dev_name="dish/leaf/001"),
                MagicMock(dev_name="dish/leaf/002"),
            ],
            ["dish/leaf/001", "dish/leaf/002"],
            2,
            id="all-responsive",
        ),
        pytest.param(
            # Second device is unresponsive, so no adapter is created for it.
            [False, True],
            [
                MagicMock(dev_name="dish/leaf/001"),
            ],
            ["dish/leaf/001"],
            1,
            id="one-unresponsive",
        ),
        pytest.param(
            # First adapter creation fails, second one succeeds.
            [False, False],
            [
                RuntimeError("adapter creation failed"),
                MagicMock(dev_name="dish/leaf/002"),
            ],
            ["dish/leaf/002"],
            2,
            id="one-adapter-creation-fails",
        ),
    ],
)
def test_get_dish_adapters(
    configure_runtime_context,
    adapter_factory,
    device_states,
    adapter_side_effect,
    expected_names,
    expected_calls,
):
    """Test get_dish_adapters for different device conditions."""

    command = LoadDishCfg(
        command_runtime_context=configure_runtime_context,
        adapter_factory=adapter_factory,
        logger=mock.Mock(),
    )

    device_names = [
        f"dish/leaf/{index:03d}" for index in range(1, len(device_states) + 1)
    ]

    configure_runtime_context.device_ctx.dish_leaf_node_dev_names = (
        device_names
    )

    configure_runtime_context.device_ctx.get_dev.side_effect = [
        MagicMock(unresponsive=state) for state in device_states
    ]

    adapter_factory.get_or_create_adapter.side_effect = adapter_side_effect

    result = command.get_dish_adapters()

    assert [adapter.dev_name for adapter in result] == expected_names

    assert adapter_factory.get_or_create_adapter.call_count == expected_calls


def test_get_dish_adapters_raises_when_no_adapter_created(
    configure_runtime_context,
    adapter_factory,
):
    """Test DishAdapterError when no adapter can be created."""

    command = LoadDishCfg(
        command_runtime_context=configure_runtime_context,
        adapter_factory=adapter_factory,
        logger=mock.Mock(),
    )

    configure_runtime_context.device_ctx.dish_leaf_node_dev_names = [
        "dish/leaf/001",
        "dish/leaf/002",
    ]

    configure_runtime_context.device_ctx.get_dev.side_effect = [
        MagicMock(unresponsive=False),
        MagicMock(unresponsive=False),
    ]

    adapter_factory.get_or_create_adapter.side_effect = RuntimeError(
        "adapter creation failed"
    )

    with pytest.raises(DishAdapterError):
        command.get_dish_adapters()


def test_get_dish_adapters_all_devices_unresponsive(
    configure_runtime_context,
    adapter_factory,
):
    """Test DishAdapterError when all devices are unresponsive."""

    command = LoadDishCfg(
        command_runtime_context=configure_runtime_context,
        adapter_factory=adapter_factory,
        logger=mock.Mock(),
    )

    configure_runtime_context.device_ctx.dish_leaf_node_dev_names = [
        "dish/leaf/001",
        "dish/leaf/002",
    ]

    configure_runtime_context.device_ctx.get_dev.side_effect = [
        MagicMock(unresponsive=True),
        MagicMock(unresponsive=True),
    ]

    with pytest.raises(DishAdapterError):
        command.get_dish_adapters()

    adapter_factory.get_or_create_adapter.assert_not_called()


# ---------------------------------------------------------------------------
# _execute_on_dish
# ---------------------------------------------------------------------------


def test_execute_on_dish(
    configure_runtime_context,
    adapter_factory,
):
    """Test execution of SetKValue commands on dish adapters."""

    command = LoadDishCfg(
        command_runtime_context=configure_runtime_context,
        adapter_factory=adapter_factory,
        logger=mock.Mock(),
    )

    dish_adapters = [
        MagicMock(dev_name="dish/leaf/001"),
        MagicMock(dev_name="dish/leaf/002"),
    ]

    command.plan = MagicMock()
    command.plan.dish_parameters = {
        "001": {"k": 10},
        "002": {"k": 20},
    }

    command.get_dish_adapters = MagicMock(return_value=dish_adapters)

    with patch(
        "ska_tmc_centralnode.refactored_commands.load_dish_cfg.load_dish_config_command.DishKValueExecutor"
    ) as executor_cls:
        executor = executor_cls.return_value

        command._execute_on_dish()

        command.get_dish_adapters.assert_called_once_with()

        executor_cls.assert_called_once_with(
            dish_adapters=dish_adapters,
            command_id=command.context.command_id,
            invoke_callback_factory=command.async_cb,
            add_device_command=command.context.device_commands.append,
            add_device_name=(configure_runtime_context.append_dish_dev_names),
            update_kvalue_aggregator=(
                configure_runtime_context.update_kval_aggregator
            ),
            logger=command.logger,
        )

        executor.execute.assert_called_once_with(command.plan.dish_parameters)

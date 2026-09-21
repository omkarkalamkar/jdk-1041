import json
import threading
from unittest.mock import MagicMock

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.v4.command_context import CommandResult
from ska_tmc_common.v4.exceptions.exceptions import CommandInvocationError

from ska_tmc_centralnode.refactored_commands.set_stow_mode.set_stow_command import (
    SetStowMode,
)
from tests.settings import DISH_LEAF_NODE_DEVICE, create_cm, logger


def test_cm_set_stow_mode_success(
    tango_context,
    task_callback,
):
    cm, _ = create_cm()
    argin = json.dumps(["ska001", "ska002"])
    cm.set_stow_mode(argin, task_callback, task_abort_event=threading.Event())
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.OK,
                "SetStowMode succeeded on provided ['ska001', 'ska002'] dishes.",
            ),
        },
        lookahead=5,
    )


def test_cm_set_stow_mode_all_dishes_exception(task_callback):
    cm, adapter_factory = create_cm()
    adapter_factory = MagicMock()
    cm.adapter_factory = adapter_factory
    cm.logger = MagicMock()

    cm.get_dish_leaf_node_device_names = MagicMock(
        return_value=[
            "ska_mid/dish/ska001",
            "ska_mid/dish/ska002",
        ]
    )
    cm.submit_task = MagicMock(
        return_value=(ResultCode.OK, "Command Completed")
    )
    argin = json.dumps(["ALL", "ska001"])
    cm.set_stow_mode(
        argin, task_callback=task_callback, task_abort_event=threading.Event()
    )
    cm.logger.exception.assert_called_once()




def test_get_current_dish_mode_of_dln():
    cm, _ = create_cm()
    dish_id = "ska001"
    expected_mode = 5  # DishMode.STOW
    cm.get_dish_leaf_node_device_names = MagicMock(
        return_value=[
            "ska_mid/dish/ska001",
            "ska_mid/dish/ska002",
        ]
    )
    mock_device = MagicMock()
    mock_device.dish_mode = expected_mode
    cm.component = MagicMock()
    cm.component.get_device.return_value = mock_device
    result = cm.get_current_dish_mode_of_dln(dish_id)
    cm.get_dish_leaf_node_device_names.assert_called_once()
    assert result == expected_mode


def test_update_task_status(task_callback):
    cm, _ = create_cm()
    cm.stow_mode_aggregated_result = False
    adapter_factory = MagicMock
    set_stow_command = SetStowMode(
        cm._get_stow_context(),
        adapter_factory,
        logger=MagicMock(),
    )
    set_stow_command.process_update_task_for_command_failure = MagicMock()
    set_stow_command.update_task_status(
        result=[ResultCode.FAILED, "exception"]
    )
    set_stow_command.process_update_task_for_command_failure.assert_called_once()
    set_stow_command.receptors_with_stow_mode_set = ["ska001"]
    cm.stow_mode_aggregated_result = True
    set_stow_command.dishln_stow_mode_cmd_exe_data = {
        "ska002": {"result_code": [0, "success"]}
    }
    set_stow_command.context.task_callback = MagicMock()
    set_stow_command.update_task_status(
        result=[ResultCode.OK, "Success"],
        exception="",
    )
    set_stow_command.logger.debug.assert_called_once()
    set_stow_command.context.task_callback.assert_called_once()
    kwargs = set_stow_command.context.task_callback.call_args.kwargs
    message = kwargs["result"][1]
    assert (
        message
        == "SetStowMode succeeded on provided ['ska001', 'ska002'] dishes."
    )


def test_process_update_task_for_command_failure():
    cm, _ = create_cm()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm._get_stow_context(),
        adapter_factory,
        logger=MagicMock(),
    )
    error_message = "SetStowMode failed"
    set_stow_command.dishln_stow_mode_cmd_exe_data = {
        "ska002": {"result_code": [3, "FAILED"]}
    }
    set_stow_command.context.task_callback = MagicMock()
    set_stow_command.process_update_task_for_command_failure(
        error_message=error_message,
    )
    set_stow_command.context.task_callback.assert_called()
    kwargs = set_stow_command.context.task_callback.call_args.kwargs

    assert kwargs["status"] == TaskStatus.COMPLETED
    assert kwargs["result"][0] == ResultCode.FAILED
    assert error_message in kwargs["result"][1]
    assert error_message in kwargs["exception"]


def test_set_stow_mode_do():
    cm, _ = create_cm()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm._get_stow_context(),
        adapter_factory,
        logger=MagicMock(),
    )
    set_stow_command.execute(argin="", task_callback=MagicMock())
    kwargs = set_stow_command.context.task_callback.call_args.kwargs
    result_code = kwargs["result"][0]
    message = kwargs["result"][1]
    assert result_code == ResultCode.FAILED
    assert "argin is empty" in message
    set_stow_command.executor._adapter_provider.get_or_create_adapter = (
        MagicMock(return_value=None)
    )
    set_stow_command.execute(argin=["ska001"], task_callback=MagicMock())
    kwargs = set_stow_command.context.task_callback.call_args.kwargs

    result_code = kwargs["result"][0]
    message = kwargs["result"][1]
    assert result_code == ResultCode.FAILED
    assert "Error in creating dish adapters" in message

    set_stow_command.executor.execute = MagicMock()

    def _set_failure():
        set_stow_command.context.results = {
            DISH_LEAF_NODE_DEVICE: CommandResult(
                DISH_LEAF_NODE_DEVICE, ResultCode.FAILED, "Failed"
            )
        }

    def _set_success():
        set_stow_command.context.results = {
            DISH_LEAF_NODE_DEVICE: CommandResult(
                DISH_LEAF_NODE_DEVICE, ResultCode.OK, "Completed"
            )
        }

    timer = threading.Timer(0.1, _set_failure)
    timer.start()
    set_stow_command.execute(argin=["ska001"], task_callback=MagicMock())
    kwargs = set_stow_command.context.task_callback.call_args.kwargs
    result_code = kwargs["result"][0]
    message = kwargs["result"][1]
    assert result_code == ResultCode.FAILED
    assert "Failed" in message
    timer = threading.Timer(0.1, _set_success)
    timer.start()
    set_stow_command.execute(argin=["ska001"], task_callback=MagicMock())
    kwargs = set_stow_command.context.task_callback.call_args.kwargs
    result_code = kwargs["result"][0]
    message = kwargs["result"][1]
    assert result_code == ResultCode.OK
    assert "SetStowMode succeeded" in message


def test_set_stow_mode_to_dish():
    cm, _ = create_cm()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm._get_stow_context(),
        adapter_factory,
        logger=MagicMock(),
    )
    set_stow_command.executor._adapter_provider.get_or_create_adapter = (
        MagicMock(return_value=None)
    )
    set_stow_command.execute(argin=["ska001"], task_callback=MagicMock())
    set_stow_command.logger.error.assert_called_once_with(
        "Dish is unreachable"
    )
    set_stow_command.logger = logger
    set_stow_command.command_runtime_context.get_current_dish_mode_of_dln = (
        MagicMock(return_value=5)
    )
    set_stow_command.execute(argin=["ska001"], task_callback=MagicMock())
    kwargs = set_stow_command.context.task_callback.call_args.kwargs
    result_code = kwargs["result"][0]
    message = kwargs["result"][1]
    assert ResultCode.OK == result_code
    assert "SetStowMode succeeded" in message
    assert "ska001" in set_stow_command.receptors_with_stow_mode_set


def test_set_stow_mode_to_dish_normal_execution():
    cm, _ = create_cm()
    dish_id = "ska001"
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm._get_stow_context(),
        adapter_factory,
        logger=logger,
    )
    adapter = MagicMock()
    adapter.dev_name = DISH_LEAF_NODE_DEVICE
    set_stow_command.executor._adapter_provider.get_or_create_adapter = (
        MagicMock(return_value=adapter)
    )
    set_stow_command.command_runtime_context.get_current_dish_mode_of_dln = (
        MagicMock(return_value=2)
    )

    # Command Failed
    def _set_failure():
        set_stow_command.dishln_stow_mode_cmd_exe_data = {
            dish_id: {"result_code": None}
        }
        set_stow_command.update_stow_results(
            DISH_LEAF_NODE_DEVICE,
            "",
            json.dumps((ResultCode.FAILED, "Failed")),
        )
        set_stow_command.context.results = {
            DISH_LEAF_NODE_DEVICE: CommandResult(
                DISH_LEAF_NODE_DEVICE, ResultCode.FAILED, "Failed"
            )
        }

    timer = threading.Timer(0.1, _set_failure)
    timer.start()
    set_stow_command.execute(argin=["ska001"], task_callback=MagicMock())
    kwargs = set_stow_command.context.task_callback.call_args.kwargs
    result_code = kwargs["result"][0]
    message = kwargs["result"][1]
    assert ResultCode.FAILED == result_code
    assert (
        "Exception occurred on devices: mid-tmc/leaf-node-dish/ska001: Failed"
        in message
    )
    assert '{"ska001": {"result_code": [3, "Failed"]}' in message
    # Command Raised an Exception
    adapter.invoke_command = MagicMock(
        side_effect=CommandInvocationError(
            "Error in calling SetStowMode command",
        )
    )
    set_stow_command.execute(argin=["ska001"], task_callback=MagicMock())
    kwargs = set_stow_command.context.task_callback.call_args.kwargs
    result_code = kwargs["result"][0]
    message = kwargs["result"][1]
    assert ResultCode.FAILED == result_code
    assert "Error in calling SetStowMode command" in message

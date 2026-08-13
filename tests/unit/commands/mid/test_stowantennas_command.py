import json
import threading
from unittest.mock import MagicMock, patch

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode.commands.stow_antennas_command import SetStowMode
from tests.settings import create_cm, logger


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


def test_cm_set_stow_mode_all_dishes(
    tango_context,
    task_callback,
):
    """Test SetStowMode command with ALL dishes"""
    cm, _ = create_cm()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        component_manager=cm,
        adapter_factory=adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=logger,
    )

    # Set up the component manager's stow mode data
    cm.dishln_stow_mode_cmd_exe_data = {
        "ska001": {"result_code": [0, "Command Completed"]},
        "ska002": {"result_code": [0, "Command Completed"]},
    }

    # Mock get_dish_leaf_node_device_names to return dish list
    cm.get_dish_leaf_node_device_names = MagicMock(
        return_value=[
            "ska_mid/dish/ska001",
            "ska_mid/dish/ska002",
        ]
    )

    # Mock the _set_stow_mode_to_dish to avoid actual device calls
    with patch.object(
        set_stow_command,
        "_set_stow_mode_to_dish",
        return_value=([ResultCode.OK], ["SetStowMode Command Completed"]),
    ):
        # Mock wait_for_command_completion to complete immediately
        with patch.object(
            set_stow_command,
            "wait_for_command_completion",
            return_value=(ResultCode.OK, ""),
        ):
            result, message = set_stow_command.apply_stow_mode(
                argin=["ALL"],
                task_callback=task_callback,
                task_abort_event=MagicMock(),
            )

    # Verify the result
    assert result == ResultCode.OK

    # Verify task callback was called with correct status transitions
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
        lookahead=2,
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


def test_get_set_stow_mode_resultcode():
    cm, _ = create_cm()
    cm.stow_mode_command_aggregated_result = ResultCode.OK
    assert cm.get_set_stow_mode_resultcode() == ResultCode.OK


def test_reset_stow_mode_data():
    cm, _ = create_cm()
    cm.logger = MagicMock()
    cm.reset_stow_mode_data()
    assert cm.stow_mode_command_aggregated_result == ResultCode.UNKNOWN
    assert not cm.dishln_stow_mode_cmd_exe_data
    assert not cm.number_of_stow_mode_executed
    assert not cm.command_in_progress
    assert not cm.command_mapping
    cm.logger.debug.assert_called_once()


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
    cm.component.get_device.call_count >= 1
    assert result == expected_mode


def test_apply_set_stow_command(task_callback):
    cm, _ = create_cm()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm,
        adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=MagicMock(),
    )
    set_stow_command.do = MagicMock(
        return_value=(
            [ResultCode.OK],
            ["Command Comleted"],
        )
    )
    set_stow_command.apply_stow_mode(
        argin=["ska001"],
        task_callback=task_callback,
        task_abort_event=MagicMock(),
    )
    assert set_stow_command.receptors == ["ska001"]


def test_update_task_status(task_callback):
    cm, _ = create_cm()
    cm.stow_mode_aggregated_result = False
    adapter_factory = MagicMock
    set_stow_command = SetStowMode(
        cm,
        adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=MagicMock(),
    )
    set_stow_command.process_update_task_for_command_failure = MagicMock()
    set_stow_command.update_task_status([ResultCode.FAILED, "exception"])
    set_stow_command.process_update_task_for_command_failure.assert_called_once()
    set_stow_command.receptors_with_stow_mode_set = ["ska001"]
    cm.reset_stow_mode_data = MagicMock()
    cm.stow_mode_aggregated_result = True
    cm.dishln_stow_mode_cmd_exe_data = {
        "ska002": {"result_code": [0, "success"]}
    }
    set_stow_command.task_callback = MagicMock()
    set_stow_command.update_task_status(
        [ResultCode.OK, "Success"],
        exception="",
    )
    set_stow_command.logger.debug.assert_called_once()
    set_stow_command.task_callback.assert_called_once()
    kwargs = set_stow_command.task_callback.call_args.kwargs
    message = kwargs["result"][1]
    assert (
        message
        == "SetStowMode succeeded on provided ['ska001', 'ska002'] dishes."
    )
    cm.reset_stow_mode_data.assert_called_once()


def test_process_update_task_for_command_failure():
    cm, _ = create_cm()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm,
        adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=MagicMock(),
    )
    error_message = "SetStowMode failed"
    cm.dishln_stow_mode_cmd_exe_data = {
        "ska002": {"result_code": [3, "FAILED"]}
    }
    set_stow_command.task_callback = MagicMock()
    set_stow_command.process_update_task_for_command_failure(
        error_message=error_message,
    )
    set_stow_command.task_callback.assert_called()
    kwargs = set_stow_command.task_callback.call_args.kwargs

    assert kwargs["status"] == TaskStatus.COMPLETED
    assert kwargs["result"][0] == ResultCode.FAILED
    assert error_message in kwargs["result"][1]
    assert error_message in kwargs["exception"]


def test_set_stow_mode_do():
    cm, _ = create_cm()
    adapter_factory = MagicMock()
    logger = MagicMock()
    set_stow_command = SetStowMode(
        cm,
        adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=logger,
    )
    result_code, message = set_stow_command.do(argin="")
    assert result_code[0] == ResultCode.FAILED
    assert "argin is empty" in message[0]
    set_stow_command.init_adapters = MagicMock(
        return_value=(ResultCode.FAILED, "Failed")
    )
    result_code, message = set_stow_command.do(argin=["ska001"])
    assert result_code[0] == ResultCode.FAILED
    assert "Failed" in message[0]

    set_stow_command._set_stow_mode_to_dish = MagicMock(
        return_value=([ResultCode.FAILED], ["Failed"])
    )
    set_stow_command.init_adapters = MagicMock(
        return_value=(ResultCode.OK, "Success")
    )
    result_code, message = set_stow_command.do(argin=["ska001"])
    assert result_code[0] == ResultCode.FAILED
    assert "Failed" in message[0]
    set_stow_command._set_stow_mode_to_dish = MagicMock(
        return_value=([ResultCode.OK], ["Success"])
    )
    result_code, message = set_stow_command.do(argin=["ska001"])
    assert result_code == ResultCode.OK
    assert "Command Completed" in message


def test_set_stow_mode_to_dish():
    cm, _ = create_cm()
    adapter_factory = MagicMock()
    logger = MagicMock()
    set_stow_command = SetStowMode(
        cm,
        adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=logger,
    )
    adapter = MagicMock()
    set_stow_command.add_data_to_stow_mode_dictionary_in_case_of_error = (
        MagicMock()
    )
    result_code, message = set_stow_command._set_stow_mode_to_dish(["ska001"])
    logger.error.assert_called_once()
    assert ResultCode.OK in result_code
    assert "SetStowMode Command Completed" in message
    set_stow_command.add_data_to_stow_mode_dictionary_in_case_of_error.assert_called_once_with(
        "ska001",
        "Dish is unreachable",
    )

    # Dish is already in stow mode
    adapter.dev_name = "ska_mid/dish/ska001"
    set_stow_command.dish_adapters = [adapter]
    cm.get_current_dish_mode_of_dln = MagicMock(return_value=5)
    result_code, message = set_stow_command._set_stow_mode_to_dish(["ska001"])
    assert ResultCode.OK in result_code
    assert "SetStowMode Command Completed" in message
    assert "ska001" in set_stow_command.receptors_with_stow_mode_set


def test_set_stow_mode_to_dish_normal_execution():
    cm, _ = create_cm()
    dish_id = "ska001"
    logger = MagicMock()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm,
        adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=logger,
    )
    adapter = MagicMock()
    adapter.dev_name = "ska_mid/dish/ska001"
    set_stow_command.dish_adapters = [adapter]
    cm.get_current_dish_mode_of_dln = MagicMock(return_value=2)

    # Command Failed
    set_stow_command.invoke_command = MagicMock(
        return_value=(
            [int(ResultCode.FAILED)],
            ["Error in calling SetStowMode command"],
        )
    )

    set_stow_command.set_stow_mode_cm_variables = MagicMock()
    set_stow_command._set_stow_mode_to_dish([dish_id])
    set_stow_command.invoke_command.assert_called_once()
    set_stow_command.set_stow_mode_cm_variables.assert_called_once_with(
        dish_id, False
    )

    assert dish_id in cm.dishln_stow_mode_cmd_exe_data
    err_msg = "Error in calling SetStowMode command on ska001 Dish Leaf Node"
    assert err_msg in cm.dishln_stow_mode_cmd_exe_data[dish_id]["result_code"]
    assert logger.info.call_count >= 1

    # Command Raised an Exception
    set_stow_command.invoke_command = MagicMock(
        side_effect=Exception("Error in Calling SetStowMode command")
    )
    set_stow_command._set_stow_mode_to_dish([dish_id])
    assert logger.exception.call_count >= 1

    # Command Started with OK
    set_stow_command.invoke_command = MagicMock(
        return_value=(
            [int(ResultCode.STARTED)],
            ["Command Completed"],
        )
    )
    set_stow_command.set_stow_mode_cm_variables = MagicMock()
    set_stow_command._set_stow_mode_to_dish([dish_id])
    set_stow_command.invoke_command.assert_called_once()
    set_stow_command.set_stow_mode_cm_variables.assert_called_once_with(
        dish_id, True
    )


def test_set_stow_mode_cm_variables():
    cm, _ = create_cm()
    dish_id = "ska001"
    logger = MagicMock()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm,
        adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=logger,
    )
    set_stow_command.set_stow_mode_cm_variables(dish_id=dish_id, flag=True)
    assert cm.number_of_stow_mode_executed
    assert cm.dishln_stow_mode_cmd_exe_data
    cm.dishln_stow_mode_cmd_exe_data = {}
    set_stow_command.set_stow_mode_cm_variables(dish_id=dish_id, flag=False)
    assert cm.dishln_stow_mode_cmd_exe_data


def test_add_data_to_stow_mode_dictionary_in_case_of_error():
    cm, _ = create_cm()
    dish_id = "ska001"
    logger = MagicMock()
    adapter_factory = MagicMock()
    set_stow_command = SetStowMode(
        cm,
        adapter_factory,
        timeout_subarrays=3,
        step_sleep=0.3,
        logger=logger,
    )
    set_stow_command.add_data_to_stow_mode_dictionary_in_case_of_error(
        dish_id, "error occurred"
    )
    assert dish_id in cm.dishln_stow_mode_cmd_exe_data

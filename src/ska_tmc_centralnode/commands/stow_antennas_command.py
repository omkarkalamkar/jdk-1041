"""Command Class for Setting Stow command on Dishes"""

import json
from typing import Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import TimeKeeper
from ska_tmc_common.enum import DishMode
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_centralnode.commands.central_node_command import SetDishGPM


# pylint:disable =abstract-method
class SetStowMode(SetDishGPM):
    """
    A class for CentralNode's SetStowMode command.
    This command invokes SetStowMode command on specified dish id's
    """

    # pylint:disable=keyword-arg-before-vararg

    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        timeout_subarrays=3,
        step_sleep=0.1,
        logger=None,
        *args,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self._timeout_subarrays = timeout_subarrays
        self._step_sleep = step_sleep
        self.receptors = []
        self.receptors_with_stow_mode_set = []
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )

    @timeout_tracker
    @error_propagation_tracker(
        "get_set_stow_mode_resultcode",
        [ResultCode.OK],
    )
    def apply_stow_mode(
        self,
        argin: list,
    ) -> Tuple[ResultCode, str]:
        """
        Applies the STOW command to specified dish id's in the list.

        Args:
            argin (list): List of dishes on which Stow needs to apply.
            logger (optional): Logger instance.
            task_callback (Callable, optional): Callback to update task status.
            task_abort_event (threading.Event, optional): task abort event.

        Returns:
            None
        """

        self.receptors = argin
        return self.do(argin)

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = None
    ) -> None:
        """
        Updates the task status for command

        Args:
            result: Result code of command
            exception (str): any message returned as a part of command

        """
        if not self.component_manager.stow_mode_aggregated_result or exception:
            error_message = (
                "SetStowMode failed: Command failure"
                " or dish not in STOW mode: "
            )
            result = self.process_update_task_for_command_failure(
                self.task_callback, error_message
            )
        else:
            self.logger.debug(
                "SetStowMode status: %s",
                self.component_manager.dishln_stow_mode_cmd_exe_data,
            )
            result = list(result)
            if self.component_manager.dishln_stow_mode_cmd_exe_data:
                cmd_stow_dishes = list(
                    self.component_manager.dishln_stow_mode_cmd_exe_data
                )
                receptors = (
                    self.receptors_with_stow_mode_set + cmd_stow_dishes
                    if self.receptors_with_stow_mode_set and cmd_stow_dishes
                    else self.receptors_with_stow_mode_set or cmd_stow_dishes
                )
            else:
                receptors = self.receptors_with_stow_mode_set
            result[
                1
            ] = f"SetStowMode succeeded on provided {receptors} dishes."
            result = tuple(result)
            self.task_callback(result=result, status=TaskStatus.COMPLETED)
        self.logger.info(
            "Command ID: %s | Calling task callback for "
            + "SetStowMode with Result: "
            + "%s and exception is : %s",
            self.component_manager.command_id,
            result,
            exception,
        )
        self.component_manager.reset_stow_mode_data()

    def process_update_task_for_command_failure(
        self, task_callback, error_message: str
    ) -> str:
        """Method to update the task callback and GPM status
        with the failure data

        Args:
            task_callback: Update task state with the failure data
        """

        keys_to_delete = []
        for (
            dish_id,
            result,
        ) in self.component_manager.dishln_stow_mode_cmd_exe_data.items():
            if not isinstance(result, str):
                if (
                    result["result_code"][0] == int(ResultCode.OK)
                    and result["dish_mode"] == DishMode.STOW.name
                ):
                    keys_to_delete.append(dish_id)
        for key in keys_to_delete:
            del self.component_manager.dishln_stow_mode_cmd_exe_data[key]
        error_message += json.dumps(
            self.component_manager.dishln_stow_mode_cmd_exe_data
        )
        task_callback(
            status=TaskStatus.COMPLETED,
            result=(ResultCode.FAILED, error_message),
            exception=error_message,
        )
        return error_message

    # pylint:disable=signature-differs
    def do(self, argin: list) -> Tuple[ResultCode, str]:
        """
        This command  invokes the SetStowMode
        command on the dish_id's specified in argin which is a
        list.

        Args:
            argin (list): gpm_data ready for execution.

        Returns:
            Tuple(ResultCode, str): Result code and message

        """
        if not argin:
            self.logger.error(
                "Command ID: %s | Provided argin is empty.",
                self.component_manager.command_id,
            )
            return [ResultCode.FAILED], [
                "Error in processing StowModeCommand, argin is empty."
            ]

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "Command ID: %s | Failed to initialize adapters: %s",
                self.component_manager.command_id,
                message,
            )
            return [result_code], [message]

        result_code, message = self._set_stow_mode_to_dish(argin)
        if result_code[0] not in [ResultCode.OK, ResultCode.STARTED]:
            return [result_code], [message]
        receptors = (
            list(self.component_manager.dishln_stow_mode_cmd_exe_data.keys())
            + self.receptors_with_stow_mode_set
        )
        self.logger.info(
            "Command ID: %s | "
            "Successfully invoked SetStowMode command on "
            " %s",
            self.component_manager.command_id,
            receptors,
        )
        return [result_code], [message]

    def _set_stow_mode_to_dish(
        self, stow_dish_list: list
    ) -> Tuple[ResultCode, str]:
        """
        Set Dish to Stow Mode by invoking SetStowMode
        command on dish leaf node.

        Args:
            stow_dish_list (list): List of dish IDs to set to stow mode

        Returns:
            Tuple(ResultCode, str): tuple containing
            ResultCode and message

        """

        return_codes = [ResultCode.UNKNOWN]
        message_or_unique_ids = []
        dishln_adapter = None
        self.logger.info(
            "Stow mode dishes for command execution: %s", stow_dish_list
        )
        try:
            for dish_id in stow_dish_list:
                dishln_adapter = [
                    adapter
                    for adapter in self.dish_adapters
                    if dish_id in adapter.dev_name
                ]
                if dishln_adapter:
                    dishln_adapter = dishln_adapter[0]
                    if (
                        DishMode.STOW
                        == self.component_manager.get_current_dish_mode_of_dln(
                            dish_id
                        )
                    ):
                        self.receptors_with_stow_mode_set.append(dish_id)
                        continue
                else:
                    error_message = "Dish is unreachable"
                    self.add_data_to_stow_mode_dictionary_in_case_of_error(
                        dish_id, error_message
                    )
                    self.logger.error(error_message)
                    continue
                err_message = (
                    f"Error in calling SetStowMode command on {dish_id}"
                    " Dish Leaf Node"
                )
                self.logger.info(
                    "Command ID: %s | Invoking stow mode command on: %s",
                    self.component_manager.command_id,
                    dishln_adapter.dev_name,
                )
                return_codes, message_or_unique_ids = self.send_command(
                    [dishln_adapter],
                    err_message,
                    "SetStowMode",
                )
                if return_codes[0] in [ResultCode.STARTED, ResultCode.OK]:
                    with self.component_manager.dishln_stow_mode_lock:
                        self.set_stow_mode_cm_variables(dish_id, True)
                else:
                    self.set_stow_mode_cm_variables(dish_id, False)
                    self.component_manager.dishln_stow_mode_cmd_exe_data[
                        dish_id
                    ] = {"result_code": err_message, "dish_mode": None}
            self.logger.info(
                "Finished executing SetStowMode on DLN."
                "Set Stow Mode data dictionary : %s",
                self.component_manager.dishln_stow_mode_cmd_exe_data,
            )
            if not self.component_manager.number_of_stow_mode_executed:
                self.component_manager.aggregate_set_stow_mode_results()
                self.component_manager.stow_mode_command_aggregated_result = (
                    ResultCode.OK
                )
                self.component_manager.observable.notify_observers(
                    attribute_value_change=True
                )
                return_codes[0] = ResultCode.OK
                message_or_unique_ids.append("SetStowMode Command Completed")
                self.logger.debug(
                    "SetStowMode return_code=%s message=%s",
                    return_codes,
                    message_or_unique_ids,
                )
        except Exception as e:
            self.logger.exception(
                "Exception occured in Calling SetStowMode, Exception: %s",
                str(e),
            )
            return [ResultCode.FAILED], [
                f"Error in Calling SetStowMode command on dish adapter {e}"
            ]

        if self.component_manager.number_of_stow_mode_executed:
            return [ResultCode.OK], [""]

        return return_codes, message_or_unique_ids

    def set_stow_mode_cm_variables(self, dish_id: str, flag: bool) -> None:
        """
        Set component manager variables for stow mode command.

        Args:
            dish_id(str): Dish leaf node identifier
            flag(bool): True to increment execution counter
        """
        if flag:
            self.component_manager.number_of_stow_mode_executed += 1
        if dish_id not in self.component_manager.dishln_stow_mode_cmd_exe_data:
            self.component_manager.dishln_stow_mode_cmd_exe_data[dish_id] = {
                "result_code": None,
                "dish_mode": None,
            }

    def add_data_to_stow_mode_dictionary_in_case_of_error(
        self, dish_id: str, error_message: str
    ) -> None:
        """
        Update the SetStowMode data with aggregated error for given
        dish_id

        Args:
            dish_id (str):
                Dish leaf node id.
            error_message (str):
                Error message.

        """
        if dish_id not in self.component_manager.dishln_stow_mode_cmd_exe_data:
            self.component_manager.dishln_stow_mode_cmd_exe_data[dish_id] = []
        self.component_manager.dishln_stow_mode_cmd_exe_data[dish_id] = (
            "ERROR: " + error_message
        )

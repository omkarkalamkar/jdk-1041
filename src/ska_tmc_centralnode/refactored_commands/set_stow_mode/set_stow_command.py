"""SetStowMode command module.

This module provides functions to execute the SetStowMode command
on the Dishes.
"""
import json
import os
from typing import Dict, Tuple, cast

from ska_control_model import ResultCode, TaskStatus
from ska_tmc_common import DishMode
from ska_tmc_common.adapters import AdapterType
from ska_tmc_common.v4.command_context import (
    CommandContext,
    CommandResult,
    DeviceCommand,
)
from ska_tmc_common.v4.command_executor import CommandExecutor
from ska_tmc_common.v4.exceptions.exceptions import (
    AdapterNotFoundError,
    CommandExecutionError,
    CommandInvocationError,
    CommandRejectedError,
)

from ..common.base_command import BaseCNCommand
from .contexts import StowContext

DISH_UNREACHABLE = "Dish is unreachable"


class SetStowExecutor(CommandExecutor):
    """Specialized executor for stow command"""

    def execute(self, context: CommandContext) -> None:
        self._logger.info(
            "Executing %d device commands",
            len(context.device_commands),
        )
        executed: int = 0
        for command in context.device_commands:
            try:
                adapter = self._adapter_provider.get_or_create_adapter(
                    command.device_name,
                    command.adapter_type,
                )

                if adapter is None:
                    context.command_invoked_callback(command, True)
                    continue

                self._invoke_command(adapter, command, context)
                executed = executed + 1
            except (CommandRejectedError, CommandInvocationError) as err:
                context.command_invoked_callback(command, True, err)
            except Exception:
                context.command_invoked_callback(command, True)

        if not executed and context.device_commands:
            dev_names = [cmd.device_name for cmd in context.device_commands]
            raise AdapterNotFoundError(
                f"Error in creating dish adapters {'.'.join(dev_names)}"
            )


class SetStowMode(BaseCNCommand):
    """A class to execute the SetStowMode command for MID.

    Executes SetStowMode command on Dish Leaf Node to stow dishes.
    """

    def __init__(
        self, command_runtime_context: StowContext, adapter_provider, logger
    ):
        super().__init__(command_runtime_context, adapter_provider, logger)
        self.receptors_with_stow_mode_set: list[str] = []
        self.command_runtime_context: StowContext = command_runtime_context
        self.dishln_stow_mode_cmd_exe_data: Dict[
            str, str | Dict[str, Tuple]
        ] = {}
        self.executor = SetStowExecutor(
            adapter_provider=adapter_provider,
            logger=logger,
        )

    def command_invoked_callback(
        self,
        cmd_ctx: DeviceCommand,
        adapter_failure: bool = False,
        error_message: str = DISH_UNREACHABLE,
    ) -> None:
        """The callback to process the command details after invocation.

        :param cmd_ctx: The device command object with details related
            to current invoked command.
        :type cmd_ctx: DeviceCommand
        """
        dish_id = cmd_ctx.device_name.split("/")[-1]
        if adapter_failure and error_message == DISH_UNREACHABLE:
            self.dishln_stow_mode_cmd_exe_data.update({dish_id: error_message})
            self.logger.error(error_message)

            self.context.results[cmd_ctx.device_name] = CommandResult(
                cmd_ctx.device_name,
                ResultCode.OK,
                error_message,
            )
        elif adapter_failure:
            self.dishln_stow_mode_cmd_exe_data.update(
                {
                    dish_id: {
                        "result_code": (ResultCode.FAILED, str(error_message))
                    }
                }
            )
            self.logger.error(error_message)

            self.context.results[cmd_ctx.device_name] = CommandResult(
                cmd_ctx.device_name,
                ResultCode.FAILED,
                str(error_message),
            )
        else:
            self.dishln_stow_mode_cmd_exe_data.update(
                {dish_id: {"result_code": None}}
            )

    def prepare_command(self) -> None:
        """
        Prepare the command for execution.
        """
        if not self.context.argin:
            raise CommandExecutionError(
                "Error in processing StowModeCommand, argin is empty."
            )
        self.context.command_invoked_callback = self.command_invoked_callback
        self.command_runtime_context.update_cmd_name(self.__class__.__name__)
        self.command_runtime_context.update_abort_evt(
            self.context.task_abort_event
        )

    def get_dish_ln_name(self, dish_id: str) -> str:
        """Returns full FQDN of dishln."""
        return os.path.join(
            self.command_runtime_context.dish_leaf_node_prefix, dish_id
        )

    def build_device_commands(self) -> None:
        for dish_id in self.context.argin:
            dish_ln = self.get_dish_ln_name(dish_id)
            if (
                self.command_runtime_context.get_current_dish_mode_of_dln(
                    dish_id
                )
                == DishMode.STOW
            ):
                self.receptors_with_stow_mode_set.append(dish_id)
            else:
                self.context.device_commands.append(
                    DeviceCommand(
                        dish_ln,
                        "SetStowMode",
                        AdapterType.DISH_LEAF_NODE,
                        update_event_callback=self.update_stow_results,
                    )
                )

    def update_stow_results(
        self, dev_name: str, command_id: str, result: str
    ) -> None:
        """
        This method is used to update the result returned
        from Dish leaf nodes as part of SetGlobalPointingModel
        command.
        If all events are received from all device then aggregate
        the result
        Value contains (unique_id, ResultCode)
        Args:
            dev_name (str): Name of the device who's event has been
            captured in this method
            value (tuple): longRunningCommandResult attribute event.
        """
        self.logger.info(
            "SetStowMode longRunningCommandResult event for device: "
            "%s %s, with value: %s",
            dev_name,
            command_id,
            result,
        )
        results = json.loads(result)
        dishln_id = dev_name.split("/")[-1]
        if results and self.dishln_stow_mode_cmd_exe_data.get(dishln_id, None):
            self.dishln_stow_mode_cmd_exe_data[dishln_id] = {
                "result_code": results
            }

    def process_update_task_for_command_failure(
        self, error_message: str
    ) -> None:
        """Method to update the task callback and GPM status
        with the failure data

        Args:
            error_message: Failure message
        """
        dish_ids: list = list(self.dishln_stow_mode_cmd_exe_data)
        for dish_id in dish_ids:
            result = self.dishln_stow_mode_cmd_exe_data.get(dish_id)
            if (
                isinstance(result, dict)
                and result["result_code"]
                and result["result_code"][0] == int(ResultCode.OK)
            ):
                self.dishln_stow_mode_cmd_exe_data.pop(dish_id)
        error_message += json.dumps(self.dishln_stow_mode_cmd_exe_data)
        self.context.task_callback(
            status=TaskStatus.COMPLETED,
            result=(ResultCode.FAILED, error_message),
            exception=error_message,
        )

    def update_task_status(self, **kwargs):
        result = cast(Tuple[ResultCode, str], kwargs.get("result"))
        status = kwargs.get("status", TaskStatus.COMPLETED)
        exception = kwargs.get("exception", "")

        if result[0] != ResultCode.OK:
            error_message = (
                exception + "SetStowMode failed: Command failure"
                " or dish not in STOW mode: "
            )
            self.process_update_task_for_command_failure(error_message)
        else:
            self.logger.debug(
                "SetStowMode status: %s",
                self.dishln_stow_mode_cmd_exe_data,
            )
            if self.dishln_stow_mode_cmd_exe_data:
                cmd_stow_dishes = list(self.dishln_stow_mode_cmd_exe_data)
                receptors = (
                    self.receptors_with_stow_mode_set + cmd_stow_dishes
                    if self.receptors_with_stow_mode_set and cmd_stow_dishes
                    else self.receptors_with_stow_mode_set or cmd_stow_dishes
                )
            else:
                receptors = self.receptors_with_stow_mode_set
            msg = f"SetStowMode succeeded on provided {receptors} dishes."
            result = (result[0], msg)
            self.context.task_callback(result=result, status=status)
        self.dishln_stow_mode_cmd_exe_data.clear()

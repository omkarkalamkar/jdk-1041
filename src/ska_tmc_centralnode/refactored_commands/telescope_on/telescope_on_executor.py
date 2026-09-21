"""
Executor for TelescopeOn command.

Tries every device command even when individual invocations fail,
preserving the original TelescopeOn behaviour of attempting all dishes.
"""

from __future__ import annotations

from ska_control_model import ResultCode
from ska_tmc_common.v4.command_context import (
    CommandContext,
    CommandResult,
    DeviceCommand,
)
from ska_tmc_common.v4.command_executor import CommandExecutor
from ska_tmc_common.v4.exceptions.exceptions import (
    CommandInvocationError,
    CommandRejectedError,
)


class TelescopeOnExecutor(CommandExecutor):
    """
    Executor that tries *every* device command.
    Individual failures are recorded via the normal result path
    but do not stop the remaining commands.
    """

    def execute(self, context: CommandContext) -> None:
        """
        Execute every device command, recording failures without aborting the
        loop.

        Unlike the default ``CommandExecutor``, this implementation continues
        after individual device failures so that all dishes / subsystems are
        attempted.

        Args:
            context (CommandContext): Context containing the list of
                ``DeviceCommand`` objects to execute and the shared result
                storage.
        """
        self._logger.info(
            "Executing %d device commands (continue-on-error)",
            len(context.device_commands),
        )
        for command in context.device_commands:
            self._execute_single_command(command, context)

    def _execute_single_command(
        self, command: DeviceCommand, context: CommandContext
    ) -> None:
        """
        Invoke a single device command.

        Any failure (adapter missing, rejected, invocation error or unexpected
        exception) is recorded via the command-invoked callback and does not
        stop the remaining commands.

        Args:
            command (DeviceCommand): The device command to invoke.
            context (CommandContext): Shared command context used to store
                results and to notify the invocation callback.
        """
        try:
            adapter = self._adapter_provider.get_or_create_adapter(
                command.device_name,
                command.adapter_type,
            )
            if adapter is None:
                self._record_and_notify_failure(
                    command,
                    context,
                    error=None,
                    message=f"No adapter found for {command.device_name}",
                )
                return

            self._invoke_command(adapter, command, context)

        except (CommandRejectedError, CommandInvocationError) as err:
            self._record_and_notify_failure(command, context, err)
        except Exception as err:  # pylint: disable=broad-except
            self._logger.exception(
                "Unexpected error invoking %s on %s",
                command.command_name,
                command.device_name,
            )
            self._record_and_notify_failure(command, context, err)

    def _record_and_notify_failure(
        self,
        command: DeviceCommand,
        context: CommandContext,
        error: Exception | None = None,
        message: str | None = None,
    ) -> None:
        """
        Store a FAILED result for the device and notify the invocation
        callback.

        This ensures ``evaluate_result`` sees the failure (matching the
        original TelescopeOn behaviour where any dish exception returned
        ResultCode.FAILED) while still allowing remaining commands to run.

        Args:
            command (DeviceCommand): The device command that failed.
            context (CommandContext): Shared command context.
            error (Exception | None): Exception that caused the failure.
            message (str | None): Explicit failure message when no exception.
        """
        if message is None:
            if error is not None:
                message = str(error)
            else:
                message = (
                    f"Error in calling {command.command_name}() "
                    f"command on {command.device_name}"
                )

        # Integration tests assert the substring
        # "Error in calling command for dish devices" for dish failures.
        if command.command_name == "SetStandbyFPMode":
            if "Error in calling command for dish devices" not in message:
                message = (
                    "Error in calling command for dish devices: " + message
                )

        command_id = ""
        if hasattr(context, "command_device_ids"):
            command_id = context.command_device_ids.get(
                command.device_name, ""
            )

        context.results[command.device_name] = CommandResult(
            device_name=command.device_name,
            result_code=ResultCode.FAILED,
            message=message,
            command_id=command_id,
        )

        if context.command_invoked_callback:
            context.command_invoked_callback(command, True, error)

    def _notify_invocation_failure(
        self,
        command: DeviceCommand,
        context: CommandContext,
        error: Exception | None = None,
    ) -> None:
        """
        Backward-compatible alias used by older call sites.

        Args:
            command (DeviceCommand): The device command that failed.
            context (CommandContext): Shared command context.
            error (Exception | None): The exception that caused the failure.
        """
        self._record_and_notify_failure(command, context, error)

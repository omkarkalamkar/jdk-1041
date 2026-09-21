"""
Executor for TelescopeOn command.

Tries every device command even when individual invocations fail,
preserving the original TelescopeOn behaviour of attempting all dishes.
"""

from ska_tmc_common.v4.command_context import CommandContext, DeviceCommand
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
                self._notify_invocation_failure(command, context)
                return

            self._invoke_command(adapter, command, context)

        except (CommandRejectedError, CommandInvocationError) as err:
            self._notify_invocation_failure(command, context, err)
        except Exception as err:  # pylint: disable=broad-except
            self._logger.exception(
                "Unexpected error invoking %s on %s",
                command.command_name,
                command.device_name,
            )
            self._notify_invocation_failure(command, context, err)

    def _notify_invocation_failure(
        self,
        command: DeviceCommand,
        context: CommandContext,
        error: Exception | None = None,
    ) -> None:
        """
        Notify the command-invoked callback that a device command failed.

        Args:
            command (DeviceCommand): The device command that failed.
            context (CommandContext): Shared command context that holds the
                optional ``command_invoked_callback``.
            error (Exception | None): The exception that caused the failure,
                if any. Defaults to ``None`` when the adapter itself could not
                be created.
        """
        if context.command_invoked_callback:
            context.command_invoked_callback(command, True, error)

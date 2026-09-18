"""Base command module.

This module provides common event-callback and adapter-resolution
helpers for refactored CentralNode commands, mirroring BaseSNCommand's
role for SubarrayNode commands.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple, cast

from ska_control_model import ResultCode, TaskStatus
from ska_tmc_common import AdapterFactory
from ska_tmc_common.v4.command_context import CommandRuntimeContext
from ska_tmc_common.v4.tmc_command import BaseTMCCommand

LOGGER = logging.getLogger(__name__)
ADAPTER_INIT_ERROR = "Exception in creating adapter for %s, Exception: %s"


class BaseCNCommand(BaseTMCCommand):
    """Base class for refactored CentralNode commands."""

    def __init__(
        self,
        command_runtime_context: CommandRuntimeContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
    ) -> None:
        """Initializes the BaseCNCommand class.
        :param command_runtime_context: Command context
            to manage data from commands.
        :type command_runtime_context: Context_T
        :param adapter_provider: Instance of adapter factory to fetch
            requried adapters.
        :type adapter_provider: AdapterFactory
        :param logger: Instance of logger.
        :type logger: logging.Logger
        """
        super().__init__(command_runtime_context, adapter_provider, logger)
        self.subarray_id: int = 0

    def _build_command_runtime_context(self) -> CommandRuntimeContext:
        """Build (or fetch) the runtime context for this command.

        Subclasses must override this to call the appropriate
        component-manager context builder
        (e.g. ``_get_assign_context`` / ``_get_release_context``).

        :raises NotImplementedError: if not overridden by a subclass.
        """
        raise NotImplementedError(
            "Subclasses of BaseCNCommand must implement "
            "_build_command_runtime_context()"
        )

    def _update_event_callback(
        self, device_name: str, command_id: str, result: str
    ) -> None:
        """Update the event data for the following device.

        :param device_name: Device name
        :type device_name: str
        :param command_id: command id
        :type command_id: str
        :param result: result code and message in string.
        :type result: str
        """
        if result:
            self.logger.debug(
                "Got Command Result for %s %s", device_name, result
            )
            self._update_event_data_storage(device_name, command_id, result)

    def _update_event_data_storage(
        self,
        device_name: str,
        command_id: str,
        result: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Method to update event data storage.

        :param device_name: device name.
        :type device_name: str
        :param command_id: command id.
        :type command_id: str
        :param result: result data as string with resultcode and message.
        :type result: str
        :param timestamp: timestamp, defaults to now if not provided.
        :type timestamp: Optional[datetime]
        """
        if timestamp is None:
            timestamp = datetime.now()

        if self.command_runtime_context is None:
            return

        event_manager = self.command_runtime_context.get_evt_data_manager()
        event_manager.update_event_data(
            device=device_name,
            data=(command_id, result),
            received_timestamp=timestamp,
        )
        cond = self.context.completion_condition
        with cond:
            cond.notify_all()

    def _set_subarray_obs_state_to_fault_on_command_timeout(self) -> None:
        """Method to set Subarray Node ObsState to FAULT when timeout
        occurs on the subarray or one of the leaf nodes."""
        self.command_runtime_context.obs_state_ctx.change_callback(
            {"component_obsfault": None}
        )

    def get_subarray_name(self, subarray_id: int) -> str:
        """Resolve and store the adapter for the target subarray.
        return: The device name of the target subarray adapter.
        rtype: str
        """
        subarray_adapter_dev_name = (
            self.command_runtime_context.subarray_trl_prefix
            + str(subarray_id).zfill(2)
        )
        return subarray_adapter_dev_name

    def validate_subarray_id(self) -> None:
        """Validate the subarray id.

        :raises ValueError: if the subarray id is not valid.
        """
        name = self.command_runtime_context.input_parameter.subarray_dev_names
        subarray_name = self.get_subarray_name(self.subarray_id)
        if subarray_name not in name:
            raise ValueError(
                f"Subarray Id {self.subarray_id} is not existing!"
            )

    def update_task_status(self, **kwargs) -> None:
        """Update task status and clear per-command subsystem bookkeeping."""
        result = cast(Tuple[ResultCode, str], kwargs.get("result"))
        status = kwargs.get("status", TaskStatus.COMPLETED)
        exception = kwargs.get("exception", "")

        if status == TaskStatus.ABORTED:
            self.context.task_callback(
                result=(ResultCode.ABORTED, "Command has been aborted"),
                status=status,
            )
        elif result[0] == ResultCode.OK:
            self.context.task_callback(result=result, status=status)
        else:
            self.context.task_callback(
                result=(ResultCode.FAILED, result[1]),
                status=status,
                exception=exception,
            )

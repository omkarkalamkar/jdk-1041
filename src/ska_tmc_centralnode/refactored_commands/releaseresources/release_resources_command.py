"""Base ReleaseResources command module for CentralNode."""

import logging
import time
from typing import Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common import TimeKeeper, TimeoutCallback

from ska_tmc_centralnode.refactored_commands.assignresources import (
    BaseCNCommand,
)

LOGGER = logging.getLogger(__name__)


class ReleaseResources(BaseCNCommand):
    """
    A class for CentralNode's ReleaseResources() command.

    Release all the resources assigned to the given Subarray. It accepts the
    subarray id, releaseALL flag and receptorIDList in JSON string format.
    When the releaseALL flag is True, ReleaseAllResources command
    is invoked on the respective SubarrayNode. In this case, the receptorIDList
    tag is empty as all the resources of the Subarray are to be released.
    When releaseALL is False, ReleaseResources will be invoked on
    the SubarrayNode and the resources provided in receptorIDList tag, are to
    be released from the Subarray. The selective release of the resources when
    releaseALL Flag is False is not yet supported.
    """

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        *args,
        logger=None,
        **kwargs,
    ):
        resolved_logger = logger or LOGGER
        super().__init__(
            component_manager,
            adapter_factory,
            logger=resolved_logger,
            *args,
            **kwargs,
        )
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)
        self.subarray_id: int | str = ""
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, self.logger
        )

    def get_subarray_obsstate(self) -> ObsState:
        """Return obsstate of the target subarray."""
        return self.component_manager.get_subarray_obsstate(
            self.subarray_devname
        )

    def release_resources(
        self, argin: str, task_callback, task_abort_event
    ) -> Tuple[ResultCode, str]:
        """Long-running command method for ReleaseResources.

        Args:
            argin (str): Input argument for the command.
            task_callback: Updates task status.
            task_abort_event: Event to abort the task.

        Returns:
            Tuple(ResultCode, str): Result code and message.
        """
        self.component_manager.command_in_progress = "ReleaseResources"
        self.task_callback = task_callback
        self.task_abort_event = task_abort_event
        self.component_manager.abort_event = self.task_abort_event
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if argin is None:
            result, message = (
                ResultCode.FAILED,
                "ReleaseResources input is required",
            )
        else:
            self.start_release_resources()

            result, message = self.prepare_command(argin)
            if result != ResultCode.FAILED:
                result, message = self.build_device_commands()
            if result != ResultCode.FAILED:
                result, message = self.execute_command()
        self.update_task_status(result=(result, message), exception=message)
        return result, message

    def start_release_resources(self) -> None:
        """Initialize command id and standard execution log."""
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing ReleaseResources command",
            self.command_id,
        )

    def prepare_command(self, argin: str) -> Tuple[ResultCode, str]:
        """Prepare command data before device command execution."""
        raise NotImplementedError

    def execute_command(self) -> Tuple[ResultCode, str]:
        """Execute device-level ReleaseResources after preparation."""
        raise NotImplementedError

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """Update the task status for command ReleaseResources.

        Args:
            result: A tuple containing the result code and a message.
            exception (str): Exception message if the command failed.
        """
        if result[0] == ResultCode.FAILED:
            self.task_callback(
                result=result,
                status=TaskStatus.COMPLETED,
                exception=exception,
            )
            self.subarray_devname = ""
        else:
            self.task_callback(result=result, status=TaskStatus.COMPLETED)
        if self.component_manager.command_mapping.get(self.command_id):
            self.component_manager.command_mapping.pop(self.command_id)
        if hasattr(self.component_manager, "subsystem_assigned_per_subarray"):
            self.component_manager.subsystem_assigned_per_subarray.pop(
                self.subarray_id, None
            )
        if hasattr(self.component_manager, "pss_beams_assigned_per_subarray"):
            self.component_manager.pss_beams_assigned_per_subarray.pop(
                self.subarray_id, None
            )

    def release_all_resources(
        self, adapter
    ) -> Tuple[list[ResultCode], list[str]]:
        """Invoke ReleaseAllResources on the given adapter.

        Args:
            adapter: Subarray adapter.

        Returns:
            Tuple(list, list): Result codes and messages.
        """
        return self.invoke_command(
            [adapter],
            f"Error in calling ReleaseAllResources() on {adapter.dev_name}"
            " device",
            "ReleaseAllResources",
        )

    def build_device_commands(self) -> Tuple[ResultCode, str]:
        """Prepare adapters and target subarray for command invocation."""
        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        result_code, message = self.get_subarray_adapter(int(self.subarray_id))
        if result_code == ResultCode.FAILED:
            return result_code, message

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                f"Subarray Id {self.subarray_id} is not existing!",
            )
        return ResultCode.OK, ""

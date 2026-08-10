"""Base ReleaseResources command module for CentralNode."""

import logging
import time
from typing import Optional, Tuple

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
        result, message = self.do(argin)
        self.update_task_status(result=(result, message), exception=message)
        return result, message

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

    def do(self, argin: Optional[str] = None) -> Tuple[ResultCode, str]:
        """Temporary, will be removed after all command refactoring."""
        raise NotImplementedError

    def build_device_commands(self) -> Tuple[ResultCode, str]:
        """Not used by ReleaseResources; satisfies abstract interface."""
        return ResultCode.OK, ""

    def do_mid(self, *args):
        """Temporary, will be removed after all command refactoring."""

    def do_low(self, *args):
        """Temporary, will be removed after all command refactoring."""

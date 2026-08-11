"""
AssignResources Command class for CentralNode.
"""

import logging
import time
from typing import Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common import TimeKeeper, TimeoutCallback

from .base_command import BaseCNCommand

LOGGER = logging.getLogger(__name__)


class AssignResources(BaseCNCommand):
    """
    A class for CentralNode's AssignResources() command.

    Assigns resources to a given subarray. It accepts the subarray ID,
    receptor ID list, and SDP block in JSON string format.

    Upon successful execution, the 'receptor_ids' attribute of the given
    subarray is populated with the given receptors.

    Checking for duplicate allocation of resources is done.
    If already allocated, it will throw an error message regarding the prior
    existence of the resource.
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
        self.subarray_id: int | str = 0
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, self.logger
        )

    def get_subarray_obsstate(self) -> ObsState:
        """
        This method returns obsstate of subarray.
        """
        return self.component_manager.get_subarray_obsstate(
            self.subarray_devname
        )

    def assign_resources(
        self, argin: str, task_callback, task_abort_event
    ) -> Tuple[ResultCode, str]:
        """
        This is a long running command method for AssignResources command.

        It executes the do hook and invokes the AssignResources command on
        lower-level devices.

        Args:
            argin (str): Input argument for the command.

        Returns:
            Tuple(ResultCode, str): Result code and message.

        """
        self.component_manager.command_in_progress = "AssignResources"
        self.task_callback = task_callback
        self.task_abort_event = task_abort_event
        self.component_manager.abort_event = self.task_abort_event
        self.task_callback(status=TaskStatus.IN_PROGRESS)
        if argin is None:
            result, message = (
                ResultCode.FAILED,
                "AssignResources input is required",
            )
        else:
            self.start_assign_resources()

            result, message = self.prepare_command(argin)
            if result != ResultCode.FAILED:
                result, message = self.build_device_commands()
            if result != ResultCode.FAILED:
                result, message = self.execute_command()
        self.update_task_status(result=(result, message), exception=message)
        return result, message

    def prepare_command(self, argin: str) -> Tuple[ResultCode, str]:
        """Prepare command data before device command execution."""
        raise NotImplementedError

    def execute_command(self) -> Tuple[ResultCode, str]:
        """Execute device-level AssignResources after preparation."""
        raise NotImplementedError

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """
        Updates the task status for a command.

        Args:
            result: A tuple containing the result code and a message.
                The result code indicates whether the command
                succeeded or failed.
            exception (str): A string representing any exception message.
                This is used when the result indicates a failure.
                Default is an empty string.

        """
        if result[0] == ResultCode.FAILED:
            self.task_callback(
                result=result, status=TaskStatus.COMPLETED, exception=exception
            )
            self.subarray_devname = ""
        else:
            self.task_callback(result=result, status=TaskStatus.COMPLETED)
        if self.component_manager.command_mapping.get(self.command_id):
            self.component_manager.command_mapping.pop(self.command_id)

    def start_assign_resources(self) -> None:
        """Initialize command id and standard execution log."""
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing AssignResources command",
            self.command_id,
        )

    def prepare_subarray_command_target(self) -> Tuple[ResultCode, str]:
        """Initialize adapters and resolve the target subarray adapter."""
        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        return self.get_subarray_adapter(int(self.subarray_id))

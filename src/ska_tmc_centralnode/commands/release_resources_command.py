"""
ReleaseResources class for CentralNode.
"""

import time
from typing import Optional, Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common import TimeKeeper, TimeoutCallback
from ska_tmc_common.adapters import AdapterFactory

from ska_tmc_centralnode.commands.central_node_command import (
    AssignReleaseResources,
)


class ReleaseResources(AssignReleaseResources):
    """
    A class for CentralNode's ReleaseResources() command.

    Release all the resources assigned to the given Subarray. It accepts the
    subarray id, releaseALL flag and receptorIDList in JSON string format.
    When the releaseALL flag is True, ReleaseAllResources command
    is invoked on the respective SubarrayNode. In this case,the receptorIDList
    tag is empty as all the resources of the Subarray are to be released.
    When releaseALL is False, ReleaseResources will be invoked on
    the SubarrayNode and the resources provided in receptorIDList tag, are to
    be released from the Subarray. The selective release of the resources when
    releaseALL Flag is False is not yet supported.
    """

    def __init__(
        self,
        component_manager,
        adapter_factory: Optional[AdapterFactory] = None,
        *args,
        logger=None,
        **kwargs,
    ):
        # pylint:disable=keyword-arg-before-vararg
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self.my_subarray_adapter = None
        self.subarray_adapter = None
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)
        self.subarray_id = ""
        self.subarray_devname = ""
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )

    def get_subarray_obsstate(self) -> ObsState:
        """
        This method returns obsstate of subarray.

        Returns: ObsState
        """
        return self.component_manager.get_subarray_obsstate(
            self.subarray_devname
        )

    def release_resources(
        self, argin: str, task_callback, task_abort_event
    ) -> Tuple[ResultCode, str]:
        """This is a long running command method for ReleaseResources command

        :param argin: Input argument for the command
        :type argin: `str`
        :returns: Result code and message
        :rtype: `Tuple[ResultCode, str]`
        """
        self.component_manager.command_in_progress = "ReleaseResources"
        self.logger.info(
            "ReleaseResources command started | command_id=%s",
            self.command_id,
        )
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
        """
        Updates the task status for command ReleaseResources

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
                self.subarray_id
            )
        if hasattr(self.component_manager, "pss_beams_assigned_per_subarray"):
            self.component_manager.pss_beams_assigned_per_subarray.pop(
                self.subarray_id
            )

    def release_all_resources(
        self, adapter
    ) -> Tuple[list[ResultCode], list[str]]:
        """
        Releases all resources

        Args:
            adapter: Adapter

        Returns:
            Tuple(list, list): Tuple of list of ResultCodes
            and lists of messages.

        """
        return self.invoke_command(
            [adapter],
            f"Error in calling ReleaseAllResources() on {adapter.dev_name}"
            + " device",
            "ReleaseAllResources",
        )

    def do_mid(self, *args):
        """Temporary, will be removed after all command refactoring"""

    def do_low(self, *args):
        """Temporary, will be removed after all command refactoring"""

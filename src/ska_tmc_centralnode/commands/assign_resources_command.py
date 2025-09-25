"""
AssignResources Command class for CentralNode.
"""

import time
from typing import Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import AdapterFactory, TimeKeeper, TimeoutCallback
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_centralnode.commands.central_node_command import (
    AssignReleaseResources,
)


class AssignResources(AssignReleaseResources):
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
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self.tm_subarray_adapter: Optional[AdapterFactory] = None
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
        """
        return self.component_manager.get_subarray_obsstate(
            self.subarray_devname
        )

    def set_command_id(self, command_name: str) -> None:
        """
        Sets the command id for error propagation.
        :param command_name: name of the command.
        :type command_name: str
        """
        self.command_id = f"{time.time()}-{command_name}"
        self.logger.info(
            "Setting command id as %s for command: %s",
            self.command_id,
            command_name,
        )

    @timeout_tracker
    @error_propagation_tracker(
        "get_subarray_obsstate",
        [ObsState.RESOURCING, ObsState.IDLE],
        use_command_class_id=True,
    )
    def assign_resources(
        self,
        argin: str,
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
        return self.do(argin)

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
        self.component_manager.command_in_progress = ""
        if self.component_manager.command_mapping.get(self.command_id):
            self.component_manager.command_mapping.pop(self.command_id)

    def get_subarray_adapter(self, subarray_id: int) -> Tuple[ResultCode, str]:
        """
        Method for obtaining the adapter for a subarray.

        Args:
            subarray_id (int): An integer representing
                the subarray ID.

        Returns:
            A tuple containing a ResultCode
            enum value and a string message.

        """
        for adapter in self.subarray_adapters:
            if str(subarray_id) in adapter.dev_name:
                self.tm_subarray_adapter = adapter
                self.subarray_devname = adapter.dev_name

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                f"SubArray Id {subarray_id} is not existing!",
            )

        return ResultCode.OK, ""

    def do_mid(self, *args):
        """Temporary, will be removed after all command refactoring"""

    def do_low(self, *args):
        """Temporary, will be removed after all command refactoring"""

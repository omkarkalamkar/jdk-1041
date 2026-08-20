"""Base ReleaseResources command module for CentralNode.

Mirrors BaseReleaseResources for SubarrayNode: ReleaseResources-specific
behaviour shared between the Mid and Low telescope commands
(completion criteria, shared device-command construction).
"""

import logging

from ska_control_model import ObsState, ResultCode, TaskStatus
from ska_tmc_common import AdapterFactory
from ska_tmc_common.adapters import AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand

from ..common.base_command import BaseCNCommand
from .release_resources_context import ReleaseResourcesContext
from .release_resources_plan import LowReleaseResourcesPlan as LRP
from .release_resources_plan import MidReleaseResourcesPlan as MRP


class BaseReleaseResourcesCN(BaseCNCommand):
    """Shared ReleaseResources command behaviour for CentralNode."""

    command_name = "ReleaseAllResources"

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        command_runtime_context: ReleaseResourcesContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
    ) -> None:
        """Initializes the BaseAssignResources command class.

        :param command_runtime_context: AssignResources command context
            to manage data from assign resources json.
        :type command_runtime_context: AssignResourcesContext
        :param adapter_provider: Instance of adapter factory to fetch
            requried adapters.
        :type adapter_provider: AdapterFactory
        :param logger: Instance of logger.
        :type logger: logging.Logger
        """
        super().__init__(command_runtime_context, adapter_provider, logger)
        self.subarray_id: int | None = None
        self._plan: LRP | MRP | None = None

    def get_subarray_obsstate(self) -> ObsState:
        """
        This method returns obsstate of subarray.
        """
        return self.command_runtime_context.obs_state_ctx.get(
            self.get_subarray_name(int(self.subarray_id))
        )

    def is_state_complete(self) -> bool:
        """Method to check the state completion for the command.

        :return: Returns True when the state is completed else False.
        :rtype: bool
        """

        return self.get_subarray_obsstate() == ObsState.EMPTY

    def _build_subarray_device_command(self) -> DeviceCommand:
        """Method to build the TM Subarray device command.

        Shared by Mid and Low: in both telescopes the single assembled
        plan payload is sent to the target Subarray device.
        """

        return DeviceCommand(
            self.get_subarray_name(int(self.subarray_id)),
            self.command_name,
            AdapterType.SUBARRAY,
        )

    def update_task_status(self, **kwargs) -> None:
        """Update task status for ReleaseResourcesLow."""
        result = kwargs.get("result")
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

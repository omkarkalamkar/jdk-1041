"""Base ReleaseResources command module for CentralNode.

Mirrors BaseReleaseResources for SubarrayNode: ReleaseResources-specific
behaviour shared between the Mid and Low telescope commands
(completion criteria, shared device-command construction).
"""

import logging

from ska_control_model import ObsState
from ska_tmc_common import AdapterFactory
from ska_tmc_common.adapters import AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand

from ..assignresources.assign_resources_command import AssignResourcesContext
from ..assignresources.base_command import BaseCNCommand
from .release_resources_plan import LowReleaseResourcesPlan as LRP
from .release_resources_plan import MidReleaseResourcesPlan as MRP


class BaseReleaseResourcesCN(BaseCNCommand):
    """Shared ReleaseResources command behaviour for CentralNode."""

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        command_runtime_context: AssignResourcesContext,
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

    def is_state_complete(self) -> bool:
        """Method to check the state completion for the command.

        :return: Returns True when the state is completed else False.
        :rtype: bool
        """
        return (
            self.command_runtime_context.obs_state_ctx.get() == ObsState.EMPTY
        )

    def _build_subarray_device_command(self) -> DeviceCommand:
        """Method to build the TM Subarray device command.

        Shared by Mid and Low: in both telescopes the single assembled
        plan payload is sent to the target Subarray device.
        """
        command_input = self._plan.payload if self._plan else ""
        return DeviceCommand(
            self.tm_subarray_adapter.dev_name,
            self.command_name,
            AdapterType.SUBARRAY,
            command_input,
        )

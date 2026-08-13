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

from ..assignresources.base_command import BaseCNCommand
from .release_resources_plan import LowReleaseResourcesPlan as LRP
from .release_resources_plan import MidReleaseResourcesPlan as MRP


class BaseReleaseResourcesCN(BaseCNCommand):
    """Shared ReleaseResources command behaviour for CentralNode."""

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        component_manager,
        adapter_factory: AdapterFactory = None,
        *args,
        logger: logging.Logger = None,
        **kwargs,
    ) -> None:
        """Initializes the BaseReleaseResourcesCN command class.

        :param component_manager: CentralNode component manager instance.
        :param adapter_factory: Instance of adapter factory to fetch
            required adapters.
        :type adapter_factory: AdapterFactory
        :param logger: Instance of logger.
        :type logger: logging.Logger
        """
        super().__init__(
            component_manager, adapter_factory, *args, logger=logger, **kwargs
        )
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
            self._update_event_callback,
        )

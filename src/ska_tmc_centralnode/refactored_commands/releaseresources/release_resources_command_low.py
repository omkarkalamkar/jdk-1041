"""ReleaseResourcesLow command class for CentralNode."""

import logging

from ska_tmc_common import AdapterFactory
from ska_tmc_common.adapters import AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand

from .release_resources_command import BaseReleaseResourcesCN
from .release_resources_context import LowReleaseResourcesContext
from .release_resources_plan import LowReleaseResourcesPlan
from .release_resources_preparation import ReleaseResourcesPreparation
from .release_resources_strategy import LowReleaseResourcesStrategy


class ReleaseResourcesLow(BaseReleaseResourcesCN):
    """Release Resources command class for telescope Low."""

    def __init__(
        self,
        command_runtime_context: LowReleaseResourcesContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
        is_auto_recovery_enabled: bool,
    ) -> None:
        """Initializes the ReleaseAllResources command class.

        :param command_runtime_context: ReleaseAllResources command context
            to manage data from assign resources json.
        :type command_runtime_context: LowReleaseResourcesContext
        :param adapter_provider: Instance of adapter factory to fetch
            requried adapters.
        :type adapter_provider: AdapterFactory
        :param logger: Instance of logger.
        :type logger: logging.Logger
        :param is_auto_recovery_enabled: Flag indicating if
            auto-recovery is enabled.
        :type is_auto_recovery_enabled: bool
        """
        super().__init__(command_runtime_context, adapter_provider, logger)
        self.is_auto_recovery_enabled = is_auto_recovery_enabled
        self._strategy: LowReleaseResourcesStrategy = (
            command_runtime_context.make_strategy(logger)
        )

    def pre_process(self, argin=None) -> None:
        """Log entry into ReleaseResources."""
        self.command_runtime_context.cmd_inprogress_ctx.update_name(
            self.__class__.__name__
        )
        self.logger.debug(
            "Executing ReleaseResources command for LOW with arguments: %s",
            argin,
        )

    def prepare_command(self) -> None:
        """Parse and normalize input data, build the plan, for LOW."""
        self.validate_subarray_id()
        self.command_runtime_context.update_abort_evt(
            self.context.task_abort_event
        )
        request = ReleaseResourcesPreparation(
            self.command_runtime_context, self.logger
        ).prepare_request(self.context.argin)

        self._plan: LowReleaseResourcesPlan = self._strategy.build_plan(
            request
        )
        self.subarray_id = self._plan.subarray_id

    def build_device_commands(self) -> None:
        """Resolve adapters and populate the device command list for LOW.
        If the plan indicates that all resources should be released, this
        method will create a DeviceCommand for the subarray and,
        if MCCS is assigned and auto-recovery is not enabled,
        a DeviceCommand for the MCCS Master Leaf Node.
        """

        if self._plan.release_all:
            self.logger.info(
                "Invoking ReleaseAllResources on subarray | device=%s",
                self.get_subarray_name(self.subarray_id),
            )
            self.context.device_commands.append(
                self._build_subarray_device_command()
            )

            if self._mccs_required():
                self.logger.info(
                    "Command ID: %s | Invoking ReleaseAllResources"
                    " on MCCS %s",
                    self.context.command_id,
                    self.command_runtime_context.mccs_mln_dev_name,
                )
                self.context.device_commands.append(
                    self._build_mccs_device_command()
                )

        self.logger.info(
            "Command ID: %s | Release Resources "
            "completed successfully on: %s",
            self.context.command_id,
            self.get_subarray_name(self.subarray_id),
        )

    def _build_mccs_device_command(self) -> DeviceCommand:
        """Method to build the ReleaseAllResources device command for the
        MCCS Master Leaf Node.
        return: DeviceCommand object for MCCS Master Leaf Node.
        rtype: DeviceCommand
        """
        command_input = self._plan.mccs_payload if self._plan else ""
        return DeviceCommand(
            self.command_runtime_context.mccs_mln_dev_name,
            self.command_name,
            AdapterType.MCCS_MASTER_LEAF_NODE,
            command_input,
        )

    def _mccs_required(self) -> bool:
        """Whether MCCS should be released as part of this command.
        :return: True if MCCS is assigned to the subarray and auto-recovery
            is not enabled, False otherwise.
        :rtype: bool
        """
        self.logger.debug(
            "Command %s: Auto-recovery enabled? %s, %s",
            self.context.command_id,
            self.is_auto_recovery_enabled,
            self.command_runtime_context.get_assigned_subsystems()[
                self.subarray_id
            ],
        )
        return (
            "mccs"
            in self.command_runtime_context.get_assigned_subsystems()[
                self.subarray_id
            ]
            and not self.is_auto_recovery_enabled
        )

    def update_task_status(self, **kwargs) -> None:
        """Update task status for ReleaseResourcesLow."""
        super().update_task_status(**kwargs)
        self.command_runtime_context.pop_subsystem_assigned_per_subarray_id(
            self.subarray_id
        )

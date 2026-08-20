"""AssignResourcesLow Command class for CentralNode."""

import logging

from ska_control_model import ResultCode, TaskStatus
from ska_tmc_common import AdapterFactory
from ska_tmc_common.adapters import AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand

from ska_tmc_centralnode.refactored_commands.assignresources import (
    AssignResourcesPreparation,
    LowAssignResourcesContext,
)

from .assign_resources_command import (
    BaseAssignResourcesCN,
    LowAssignResourcesPlan,
)
from .assign_resources_strategy import LowAssignResourcesStrategy


class AssignResourcesLow(BaseAssignResourcesCN):
    """A class for CentralNode's AssignResources() command for low."""

    def __init__(
        self,
        command_runtime_context: LowAssignResourcesContext,
        adapter_provider: AdapterFactory,
        is_auto_recovery_enabled: bool,
        logger: logging.Logger,
    ) -> None:
        """Initializes the AssignResources command class for Low telescope.

        :param command_runtime_context: AssignResources command context
            to manage low telescope specific data from assign resources
            json.
        :type command_runtime_context: LowAssignResourcesContext
        :param adapter_provider: Instance of adapter factory to fetch
            required adapters.
        :type adapter_provider: AdapterFactory
        :param is_auto_recovery_enabled: Flag indicating
            if auto-recovery is enabled.
        :type is_auto_recovery_enabled: bool
        :param logger: Instance of logger.
        :type logger: logging.Logger
        """
        super().__init__(command_runtime_context, adapter_provider, logger)
        self.adapter_provider = adapter_provider
        self.error_message: str | Exception = ""
        self._strategy: LowAssignResourcesStrategy = (
            command_runtime_context.make_strategy(logger)
        )
        self.is_auto_recovery_enabled = is_auto_recovery_enabled

    def pre_process(self, argin=None) -> None:
        """Log entry into AssignResources and update command
        in progress context."""

        self.command_runtime_context.cmd_inprogress_ctx.update_name(
            self.__class__.__name__
        )
        self.logger.debug(
            "Executing AssignResources command for LOW with arguments: %s",
            argin,
        )

    def prepare_command(self) -> None:
        """Parse input and build the execution plan/context for LOW."""
        self.validate_subarray_id(self.subarray_id)
        request = AssignResourcesPreparation(
            self.command_runtime_context, self.logger
        ).prepare_request(self.context.argin)
        self.command_runtime_context.update_abort_evt(
            self.context.task_abort_event
        )
        self._plan: LowAssignResourcesPlan = self._strategy.build_plan(request)
        self.command_runtime_context.apply_plan(self._plan)
        self.subarray_id = self._plan.subarray_id
        # apply_plan propagates subarray_id to context and subsystems to cm.

        self.logger.debug(
            "Command %s: Subsystems assigned for subarray %s: %s",
            self.context.command_id,
            self.subarray_id,
            self._plan.subsystems,
        )
        self.logger.info(
            "Command ID: %s | AssignResources started for subarray %s",
            self.context.command_id,
            self.subarray_id,
        )

    def build_device_commands(self) -> None:
        """Resolve target subarray/MCCS adapters and populate the device
        command list for this invocation."""

        self.context.device_commands.append(
            self._build_subarray_device_command()
        )

        if self._mccs_required():
            self.command_runtime_context.log_state(
                "Device states before executing AssignResources command"
            )
            self.logger.info(
                "Command ID: %s | Invoking AssignResources on MCCS %s",
                self.context.command_id,
                self.command_runtime_context.mccs_mln_dev_name,
            )
            self.context.device_commands.append(
                self._build_mccs_device_command()
            )

    def _build_mccs_device_command(self) -> DeviceCommand:
        """Method to build the MCCS Master Leaf Node device command.
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
        """Whether MCCS should be assigned as part of this command.
        :return: True if MCCS is assigned to the subarray and auto-recovery
            is not enabled, False otherwise.
        :rtype: bool
        """
        return (
            "mccs"
            in self.command_runtime_context.get_assigned_subsystems()[
                self.subarray_id
            ]
            and not self.is_auto_recovery_enabled
        )

    def update_task_status(self, **kwargs) -> None:
        """Update task status and clear per-command subsystem bookkeeping."""
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

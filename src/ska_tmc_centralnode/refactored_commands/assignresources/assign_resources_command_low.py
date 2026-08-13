"""AssignResourcesLow Command class for CentralNode."""

from ska_control_model import ResultCode, TaskStatus
from ska_tmc_common.adapters import AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand

from ska_tmc_centralnode.refactored_commands.assignresources import (
    AssignResourcesPreparation,
    LowAssignResourcesContext,
)

from .assign_resources_command import BaseAssignResourcesCN


class AssignResourcesLow(BaseAssignResourcesCN):
    """A class for CentralNode's AssignResources() command for low."""

    command_name = "AssignResources"

    def __init__(
        self,
        component_manager,
        *args,
        adapter_factory=None,
        logger=None,
        is_auto_recovery_enabled=False,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, *args, logger=logger, **kwargs
        )
        self.is_auto_recovery_enabled = is_auto_recovery_enabled
        self._assigned_subsystem: list = []

    def pre_process(self, argin=None) -> None:
        """Log entry into AssignResources."""
        self.logger.debug(
            "Executing AssignResources command for LOW with arguments: %s",
            argin,
        )

    def prepare_command(self) -> None:
        """Parse input and build the execution plan/context for LOW."""
        request = AssignResourcesPreparation(
            self.component_manager, self.logger
        ).prepare_request(self.context.argin)

        ctx = self._build_context()
        plan = ctx.make_strategy(self.logger).build_plan(request)

        self.subarray_id = plan.subarray_id
        # apply_plan propagates subarray_id to context and subsystems to cm.
        ctx.apply_plan(plan)

        self._plan = plan
        self._assigned_subsystem = list(plan.subsystems)
        self.logger.debug(
            "Command %s: Subsystems assigned for subarray %s: %s",
            self.context.command_id,
            self.subarray_id,
            self._assigned_subsystem,
        )
        self.logger.info(
            "Command ID: %s | AssignResources started for subarray %s",
            self.context.command_id,
            self.subarray_id,
        )

    def build_device_commands(self) -> None:
        """Resolve target subarray/MCCS adapters and populate the device
        command list for this invocation."""
        self.prepare_subarray_command_target()

        self.context.device_commands.append(
            self._build_subarray_device_command()
        )

        if self._mccs_required():
            self.component_manager.log_state(
                "Device states before executing AssignResources command"
            )
            self.logger.info(
                "Command ID: %s | Invoking AssignResources on MCCS %s",
                self.context.command_id,
                self.mccs_mln_adapter,
            )
            self.context.device_commands.append(
                self._build_mccs_device_command()
            )

    def _build_mccs_device_command(self) -> DeviceCommand:
        """Method to build the MCCS Master Leaf Node device command.

        LOW-only, so kept local rather than on the shared
        BaseAssignResourcesCN layer.
        """
        command_input = self._plan.mccs_payload if self._plan else ""
        return DeviceCommand(
            self.mccs_mln_adapter.dev_name,
            self.command_name,
            AdapterType.MCCS_MASTER_LEAF_NODE,
            command_input,
            self._update_event_callback,
        )

    def _mccs_required(self) -> bool:
        """Whether MCCS should be assigned as part of this command."""
        return (
            "mccs"
            in self.component_manager.subsystem_assigned_per_subarray[
                self.subarray_id
            ]
            and not self.is_auto_recovery_enabled
        )

    def command_invoked_callback(self, cmd_ctx: DeviceCommand) -> None:
        """Restore the generic event-manager placeholder update from
        BaseCNCommand, then additionally record subsystem assignment once
        the MCCS invocation is accepted — mirrors the original code, which
        set subsystem_assigned_per_command_id right after invoke_command
        returned an accepted (non-FAILED) result for MCCS, not after the
        device's final LRC result.
        """
        super().command_invoked_callback(cmd_ctx)
        if (
            self.mccs_mln_adapter is not None
            and cmd_ctx.device_name == self.mccs_mln_adapter.dev_name
        ):
            self.component_manager.subsystem_assigned_per_command_id[
                self.context.command_id
            ] = self._assigned_subsystem

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
                result=result, status=status, exception=exception
            )

        self.component_manager.subsystem_assigned_per_command_id.pop(
            self.context.command_id, None
        )

    def _build_context(self) -> LowAssignResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_assign_context(command=self)

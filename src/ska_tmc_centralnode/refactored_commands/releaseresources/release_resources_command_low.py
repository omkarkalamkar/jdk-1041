"""ReleaseResourcesLow command class for CentralNode."""

from ska_tmc_common.adapters import AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand

from .release_resources_command import BaseReleaseResourcesCN
from .release_resources_context import LowReleaseResourcesContext
from .release_resources_preparation import ReleaseResourcesPreparation


class ReleaseResourcesLow(BaseReleaseResourcesCN):
    """Release Resources command class for telescope Low."""

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        *args,
        is_auto_recovery_enabled: bool = True,
        logger=None,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, *args, logger=logger, **kwargs
        )
        self.is_auto_recovery_enabled = is_auto_recovery_enabled
        self._assigned_subsystem: list = []

    def pre_process(self, argin=None) -> None:
        """Log entry into ReleaseResources."""
        self.logger.debug(
            "Executing ReleaseResources command for LOW with arguments: %s",
            argin,
        )

    def prepare_command(self) -> None:
        """Parse and normalize input data, build the plan, for LOW."""
        request = ReleaseResourcesPreparation(
            self.component_manager, self.logger
        ).prepare_request(self.context.argin)

        ctx = self._build_context()
        plan = ctx.make_strategy(self.logger).build_plan(request)

        self.subarray_id = plan.subarray_id
        ctx.apply_plan(plan)
        self._plan = plan

    def build_device_commands(self) -> None:
        """Resolve adapters and populate the device command list for LOW.

        When release_all is False, no device commands are added. This
        matches the original code exactly: unlike MID, LOW did not fail
        explicitly on partial release — it silently skipped invocation
        and still proceeded to wait for the subarray to reach EMPTY. That
        no-op-but-still-wait behaviour is preserved here: leaving
        context.device_commands empty means is_complete() is satisfied
        trivially by 0 results == 0 device_commands, and completion still
        hinges on is_state_complete() reaching ObsState.EMPTY.
        """
        self.prepare_subarray_command_target()

        if self._plan.release_all:
            self.logger.info(
                "Invoking ReleaseAllResources on subarray | device=%s",
                self.tm_subarray_adapter.dev_name,
            )
            self.context.device_commands.append(
                self._build_subarray_device_command()
            )

            self._assigned_subsystem = (
                self.component_manager.subsystem_assigned_per_subarray[
                    self.subarray_id
                ]
            )
            if self._mccs_required():
                self.logger.info(
                    "Command ID: %s | Invoking ReleaseAllResources"
                    " on MCCS %s",
                    self.context.command_id,
                    self.mccs_mln_adapter,
                )
                self.context.device_commands.append(
                    self._build_mccs_device_command()
                )

        self.logger.info(
            "Command ID: %s | Release Resources "
            "completed successfully on: %s",
            self.context.command_id,
            self.tm_subarray_adapter,
        )

    def _build_mccs_device_command(self) -> DeviceCommand:
        """Method to build the ReleaseAllResources device command for the
        MCCS Master Leaf Node.

        Sends plan.mccs_payload directly. The original code did
        json.loads(self._plan.mccs_payload) immediately followed by
        json.dumps(...) with no mutation in between — a pure round trip —
        so this sends the already-serialized string as-is, same
        simplification already applied to AssignResources.
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
        """Whether MCCS should be released as part of this command."""
        return (
            "mccs"
            in self.component_manager.subsystem_assigned_per_subarray[
                self.subarray_id
            ]
            and not self.is_auto_recovery_enabled
        )

    def command_invoked_callback(self, cmd_ctx: DeviceCommand) -> None:
        """Restore the generic event-manager placeholder update, then
        additionally record subsystem assignment once the MCCS invocation
        is accepted — mirrors the original, which set
        subsystem_assigned_per_command_id right after invoke_command
        returned an accepted result for MCCS.
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
        """Update task status for ReleaseResourcesLow."""
        super().update_task_status(**kwargs)
        self.component_manager.subsystem_assigned_per_command_id.pop(
            self.context.command_id, None
        )

    def _build_context(self) -> LowReleaseResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_release_context(command=self)

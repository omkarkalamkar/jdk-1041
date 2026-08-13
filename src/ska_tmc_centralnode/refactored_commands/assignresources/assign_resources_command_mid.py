"""AssignResourcesMid Command class for CentralNode."""

from ska_control_model import ResultCode, TaskStatus

from ska_tmc_centralnode.refactored_commands.assignresources import (
    AssignResourcesPreparation,
    MidAssignResourcesContext,
)

from .assign_resources_command import BaseAssignResourcesCN


class AssignResourcesMid(BaseAssignResourcesCN):
    """A class for CentralNode's AssignResources() command for Mid."""

    command_name = "AssignResources"

    def __init__(
        self,
        component_manager,
        *args,
        adapter_factory=None,
        logger=None,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, *args, logger=logger, **kwargs
        )
        self.receptor_ids: list = []

    def pre_process(self, argin=None) -> None:
        """Log entry into AssignResources."""
        self.logger.debug(
            "Executing AssignResources command for MID with arguments: %s",
            argin,
        )

    def prepare_command(self) -> None:
        """Parse input and build the execution plan/context for MID."""
        request = AssignResourcesPreparation(
            self.component_manager, self.logger
        ).prepare_request(self.context.argin, remove_transaction_id=True)

        ctx = self._build_context()
        plan = ctx.make_strategy(self.logger).build_plan(request)

        self.subarray_id = plan.subarray_id
        ctx.apply_plan(plan)

        self._plan = plan
        self.receptor_ids = plan.receptor_ids
        self._validate_receptors()

    def _validate_receptors(self) -> None:
        """Validate requested receptors are available for assignment.

        :raises ValueError: if any requested receptor is already
            allocated.
        """
        self.logger.debug(
            "Command ID %s: Receptor IDs requested for assignment: %s",
            self.context.command_id,
            self.receptor_ids,
        )
        for receptor_id in self.receptor_ids:
            if self.component_manager.is_already_assigned(receptor_id):
                raise ValueError(f"Dish {receptor_id} is already allocated")
            self.logger.debug(
                "Command ID: %s | Dish %s is available for assignment.",
                self.context.command_id,
                self.receptor_ids,
            )

    def build_device_commands(self) -> None:
        """Resolve the target subarray adapter and populate the device
        command list for this invocation."""
        self.prepare_subarray_command_target()

        self.component_manager.log_state(
            "Device states before executing AssignResources command"
        )
        self.logger.info(
            "Command ID: %s | Invoking AssignResources command on: %s",
            self.context.command_id,
            self.tm_subarray_adapter,
        )

        self.context.device_commands.append(
            self._build_subarray_device_command()
        )

    def update_task_status(self, **kwargs) -> None:
        """Update task status for AssignResourcesMid."""
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

    def _build_context(self) -> MidAssignResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_assign_context(command=self)

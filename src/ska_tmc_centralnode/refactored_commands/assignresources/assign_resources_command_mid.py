"""AssignResourcesMid Command class for CentralNode."""

import logging

from ska_control_model import ResultCode, TaskStatus
from ska_tmc_common import AdapterFactory

from ska_tmc_centralnode.refactored_commands.assignresources import (
    AssignResourcesPreparation,
    MidAssignResourcesContext,
)

from .assign_resources_command import (
    BaseAssignResourcesCN,
    MidAssignResourcesPlan,
)
from .assign_resources_strategy import MidAssignResourcesStrategy


class AssignResourcesMid(BaseAssignResourcesCN):
    """A class for CentralNode's AssignResources() command for Mid."""

    def __init__(
        self,
        command_runtime_context: MidAssignResourcesContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
    ) -> None:
        """Initializes the AssignResources command class for Mid telescope.

        :param command_runtime_context: AssignResources command context
            to manage mid telescope specific data from assign resources
            json.
        :type command_runtime_context: MidAssignResourcesContext
        :param adapter_provider: Instance of adapter factory to fetch
            requried adapters.
        :type adapter_provider: AdapterFactory
        :param logger: Instance of logger.
        :type logger: logging.Logger
        """
        super().__init__(command_runtime_context, adapter_provider, logger)
        self._strategy: MidAssignResourcesStrategy = (
            command_runtime_context.make_strategy(logger)
        )
        self.receptor_ids: list = []

    def pre_process(self, argin=None) -> None:
        """Log entry into AssignResources and
        update command in progress context."""
        self.command_runtime_context.cmd_inprogress_ctx.update_name(
            self.__class__.__name__
        )
        self.logger.debug(
            "Executing AssignResources command for MID with arguments: %s",
            argin,
        )

    def prepare_command(self) -> None:
        """Parse input and build the execution plan/context for MID."""
        self.validate_subarray_id(self.subarray_id)
        request = AssignResourcesPreparation(
            self.command_runtime_context, self.logger
        ).prepare_request(self.context.argin, remove_transaction_id=True)
        self.command_runtime_context.update_abort_evt(
            self.context.task_abort_event
        )
        self._plan: MidAssignResourcesPlan = self._strategy.build_plan(request)
        self.subarray_id = self._plan.subarray_id

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
        for receptor_id in self._plan.receptor_ids:
            if self.command_runtime_context.is_already_assigned(receptor_id):
                raise ValueError(f"Dish {receptor_id} is already allocated")
            self.logger.debug(
                "Command ID: %s | Dish %s is available for assignment.",
                self.context.command_id,
                receptor_id,
            )

    def build_device_commands(self) -> None:
        """Resolve the target subarray adapter and populate the device
        command list for this invocation."""
        self.command_runtime_context.log_state(
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
                result=(ResultCode.FAILED, result[1]),
                status=status,
                exception=exception,
            )

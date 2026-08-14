"""ReleaseResourcesMid command class for CentralNode."""
import logging

from ska_tmc_common import AdapterFactory

from .release_resources_command import BaseReleaseResourcesCN
from .release_resources_context import MidReleaseResourcesContext
from .release_resources_plan import MidReleaseResourcesPlan
from .release_resources_preparation import ReleaseResourcesPreparation
from .release_resources_strategy import MidReleaseResourcesStrategy


class ReleaseResourcesMid(BaseReleaseResourcesCN):
    """Release Resources command class for Mid."""

    def __init__(
        self,
        command_runtime_context: MidReleaseResourcesContext,
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
        self._strategy: MidReleaseResourcesStrategy = (
            command_runtime_context.make_strategy(logger)
        )

    def pre_process(self, argin=None) -> None:
        """Log entry into ReleaseResources."""
        self.logger.debug(
            "Executing ReleaseResources command for MID with arguments: %s",
            argin,
        )

    def prepare_command(self) -> None:
        """Parse and validate input data, build the plan, for MID."""
        request = ReleaseResourcesPreparation(
            self.command_runtime_context, self.logger
        ).prepare_request(self.context.argin)
        self._plan: MidReleaseResourcesPlan = self._strategy.build_plan(
            request
        )
        self.command_runtime_context.apply_plan(self._plan)
        self.subarray_id = self._plan.subarray_id

    def build_device_commands(self) -> None:
        """Resolve the target subarray adapter and populate the device
        command list.

        Partial release is not supported for MID: matches the original
        code's explicit failure when release_all is False. Raised here,
        after adapter resolution, to preserve the original ordering
        where an adapter failure surfaced before this check.

        :raises ValueError: if release_all is False.
        """

        if not self._plan.release_all:
            raise ValueError("Partial release resources not supported!")

        self.logger.info(
            "Invoking ReleaseAllResources on subarray | device=%s",
            self.tm_subarray_adapter.dev_name,
        )
        self.context.device_commands.append(
            self._build_subarray_device_command()
        )
        self.logger.info(
            "Command ID: %s | Release Resources "
            "completed successfully on: %s",
            self.context.command_id,
            self.tm_subarray_adapter,
        )

    def update_task_status(self, **kwargs) -> None:
        """Update task status for ReleaseResourcesLow."""
        super().update_task_status(**kwargs)
        self.command_runtime_context.subsystem_assigned_per_command_id.pop(
            self.context.command_id, None
        )

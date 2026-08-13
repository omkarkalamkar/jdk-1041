"""ReleaseResourcesMid command class for CentralNode."""

from .release_resources_command import BaseReleaseResourcesCN
from .release_resources_context import MidReleaseResourcesContext
from .release_resources_preparation import ReleaseResourcesPreparation


class ReleaseResourcesMid(BaseReleaseResourcesCN):
    """Release Resources command class for Mid."""

    def pre_process(self, argin=None) -> None:
        """Log entry into ReleaseResources."""
        self.logger.debug(
            "Executing ReleaseResources command for MID with arguments: %s",
            argin,
        )

    def prepare_command(self) -> None:
        """Parse and validate input data, build the plan, for MID."""
        request = ReleaseResourcesPreparation(
            self.component_manager, self.logger
        ).prepare_request(self.context.argin)

        ctx = self._build_context()
        plan = ctx.make_strategy(self.logger).build_plan(request)

        self.subarray_id = plan.subarray_id
        ctx.apply_plan(plan)
        self._plan = plan

    def build_device_commands(self) -> None:
        """Resolve the target subarray adapter and populate the device
        command list.

        Partial release is not supported for MID: matches the original
        code's explicit failure when release_all is False. Raised here,
        after adapter resolution, to preserve the original ordering
        where an adapter failure surfaced before this check.

        :raises ValueError: if release_all is False.
        """
        self.prepare_subarray_command_target()

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

    def _build_context(self) -> MidReleaseResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_release_context(command=self)

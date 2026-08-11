"""ReleaseResourcesMid command class for CentralNode."""

from typing import Tuple

from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode

from .release_resources_command import ReleaseResources
from .release_resources_context import MidReleaseResourcesContext
from .release_resources_plan import MidReleaseResourcesPlan
from .release_resources_preparation import (
    ReleaseResourcesPreparation,
    ReleaseResourcesPreparationError,
)
from .release_resources_strategy import ReleaseResourcesPrepError


class ReleaseResourcesMid(ReleaseResources):
    """Release Resources command class for Mid."""

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
        self._plan: MidReleaseResourcesPlan | None = None

    def prepare_command(self, argin: str) -> Tuple[ResultCode, str]:
        """Parse and validate input data for MID release flow."""
        try:
            request = ReleaseResourcesPreparation(
                self.component_manager,
                self.logger,
            ).prepare_request(argin)
        except ReleaseResourcesPreparationError as exception:
            return ResultCode.FAILED, str(exception)

        ctx = self._build_context()
        try:
            plan = ctx.make_strategy(self.logger).build_plan(request)
        except ReleaseResourcesPrepError as exception:
            return ResultCode.FAILED, str(exception)

        ctx.apply_plan(plan)
        self._plan = plan
        return ResultCode.OK, ""

    def execute_command(self) -> Tuple[ResultCode, str]:
        """Execute MID release command after prepare/build lifecycle."""
        if self._plan is None:
            return ResultCode.FAILED, "ReleaseResources plan is not set"

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                f"Subarray Id {self.subarray_id} is not existing!",
            )

        if self._plan.release_all is True:
            self.logger.info(
                "Invoking ReleaseAllResources on subarray | device=%s",
                self.tm_subarray_adapter.dev_name,
            )
            return_codes, message_or_unique_ids = self.release_all_resources(
                self.tm_subarray_adapter
            )
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                    return (
                        ResultCode.FAILED,
                        message_or_unique_id,
                    )
                if return_code in [ResultCode.QUEUED, ResultCode.OK]:
                    self.component_manager.command_mapping[
                        self.command_id
                    ] = message_or_unique_id
            self.logger.info(
                "Command ID: %s | Release Resources "
                "completed successfully on: %s",
                self.command_id,
                self.tm_subarray_adapter,
            )
            return self.wait_for_command_completion(
                len(self.command_subs_list),
                ObsState.EMPTY,
                "get_subarray_obsstate",
                use_command_class_id=True,
            )
        return (
            ResultCode.FAILED,
            "Partial release resources not supported!",
        )

    def _build_context(self) -> MidReleaseResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_release_context(command=self)

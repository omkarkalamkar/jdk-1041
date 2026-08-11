"""ReleaseResourcesLow command class for CentralNode."""

import json
from typing import Tuple

from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode

from .release_resources_command import ReleaseResources
from .release_resources_context import LowReleaseResourcesContext
from .release_resources_plan import LowReleaseResourcesPlan
from .release_resources_preparation import (
    ReleaseResourcesPreparation,
    ReleaseResourcesPreparationError,
)
from .release_resources_strategy import ReleaseResourcesPrepError


class ReleaseResourcesLow(ReleaseResources):
    """Release Resources command class for telescope Low."""

    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        *args,
        is_auto_recovery_enabled: bool = True,
        logger=None,
        **kwargs,
    ):
        # pylint:disable=keyword-arg-before-vararg
        super().__init__(
            component_manager, adapter_factory, *args, logger=logger, **kwargs
        )
        self.is_auto_recovery_enabled = is_auto_recovery_enabled
        self._plan: LowReleaseResourcesPlan | None = None

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """Update task status for ReleaseResourcesLow.

        Args:
            result: A tuple containing the result code and a message.
            exception (str): Exception message if the command failed.
        """
        super().update_task_status(result, exception)
        self.component_manager.subsystem_assigned_per_subarray.pop(
            self.subarray_id, None
        )
        self.component_manager.subsystem_assigned_per_command_id.pop(
            self.command_id, None
        )
        self.component_manager.pss_beams_assigned_per_subarray.pop(
            self.subarray_id, None
        )

    def prepare_command(self, argin: str) -> Tuple[ResultCode, str]:
        """Parse and normalize input data for LOW release flow."""
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
        """Execute LOW release command after prepare/build lifecycle."""
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
            (
                return_codes,
                message_or_unique_ids,
            ) = self.release_all_resources(self.tm_subarray_adapter)
            (
                return_code,
                message_or_unique_id,
            ) = self.put_result_in_command_mapping_dict(
                return_codes, message_or_unique_ids
            )
            if return_code == ResultCode.FAILED:
                return (
                    ResultCode.FAILED,
                    message_or_unique_id,
                )
            assigned_subsystem = (
                self.component_manager.subsystem_assigned_per_subarray[
                    self.subarray_id
                ]
            )
            if (
                "mccs"
                in self.component_manager.subsystem_assigned_per_subarray[
                    self.subarray_id
                ]
                and not self.is_auto_recovery_enabled
            ):
                try:
                    input_mccs_master = json.loads(self._plan.mccs_payload)
                except Exception as exception:
                    return (
                        ResultCode.FAILED,
                        f"Error in MCCS JSON argument: {exception}",
                    )
                self.logger.info(
                    "Command ID: %s | Invoking ReleaseAllResources"
                    " on MCCS %s",
                    self.command_id,
                    self.mccs_mln_adapter,
                )
                (
                    return_codes,
                    message_or_unique_ids,
                ) = self.release_all_resources_mccs(
                    self.mccs_mln_adapter, input_mccs_master
                )
                (
                    return_code,
                    message_or_unique_id,
                ) = self.put_result_in_command_mapping_dict(
                    return_codes, message_or_unique_ids
                )
                if return_code == ResultCode.FAILED:
                    return (
                        ResultCode.FAILED,
                        message_or_unique_id,
                    )
                self.logger.info(
                    "Command ID: %s | ReleaseAllResources completed "
                    "successfully on MCCS %s",
                    self.command_id,
                    self.mccs_mln_adapter,
                )
                self.component_manager.subsystem_assigned_per_command_id[
                    self.command_id
                ] = assigned_subsystem
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

    def _build_context(self) -> LowReleaseResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_release_context(command=self)

    def release_all_resources_mccs(
        self, adapter, argin
    ) -> Tuple[list[ResultCode], list[str]]:
        """Invoke ReleaseAllResources on the MCCS master leaf node adapter.

        Args:
            adapter: MCCS master leaf node adapter.
            argin: JSON argument for the command.

        Returns:
            Tuple(list, list): Result codes and messages.
        """
        return self.invoke_command(
            [adapter],
            f"Error in calling ReleaseAllResources() on {adapter.dev_name}"
            "device",
            "ReleaseAllResources",
            json.dumps(argin),
        )

"""
AssignResourcesLow Command class for CentralNode.
"""
import json
from typing import Tuple

from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode.refactored_commands.assignresources import (
    AssignResourcesPreparation,
    AssignResourcesPreparationError,
    AssignResourcesPrepError,
    InvalidArrayLayoutError,
    MidAssignResourcesContext,
)

from .assign_resources_command import AssignResources


class AssignResourcesMid(AssignResources):
    """A class for CentralNode's AssignResources() command for Mid."""

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
        self._plan = None
        self._json_argument: dict = {}

    def execute_command(self) -> Tuple[ResultCode, str]:
        """Execute AssignResources after prepare/build lifecycle steps."""
        validation_failure = self._validate_receptors()
        if validation_failure is not None:
            return validation_failure

        result_code, message = self._invoke_assign_on_subarray()
        if result_code == ResultCode.FAILED:
            return result_code, message

        self.logger.info(
            "Command ID: %s | AssignResources completed successfully on: %s",
            self.command_id,
            self.tm_subarray_adapter,
        )

        return self.wait_for_command_completion(
            len(self.command_subs_list),
            ObsState.IDLE,
            "get_subarray_obsstate",
            use_command_class_id=True,
        )

    def prepare_command(self, argin: str) -> Tuple[ResultCode, str]:
        """Parse input and build execution plan/context for MID."""
        try:
            request = AssignResourcesPreparation(
                self.component_manager,
                self.logger,
            ).prepare_request(argin, remove_transaction_id=True)
            json_argument = request.copy_data()
        except AssignResourcesPreparationError as exception:
            return ResultCode.FAILED, str(exception)
        except InvalidArrayLayoutError as exception:
            self.logger.error(
                "Command %s: Invalid array layout: %s",
                self.command_id,
                exception,
            )
            return ResultCode.FAILED, str(exception)
        ctx = self._build_context()
        try:
            plan = ctx.make_strategy(self.logger).build_plan(request)
        except AssignResourcesPrepError as exception:
            return ResultCode.FAILED, str(exception)

        ctx.apply_plan(plan)

        # Normalize payloads using strategy output so preparation and
        # execution stay aligned.
        json_argument["csp"] = json.loads(plan.csp_payload)
        json_argument["sdp"] = json.loads(plan.sdp_payload)
        if plan.telmodel:
            json_argument["telmodel"] = plan.telmodel
        self._plan = plan
        self._json_argument = json_argument
        self.receptor_ids = plan.receptor_ids
        return ResultCode.OK, ""

    def build_device_commands(self) -> Tuple[ResultCode, str]:
        """Prepare adapters/target subarray for AssignResources invocation."""
        return self.prepare_subarray_command_target()

    def _validate_receptors(
        self,
    ) -> Tuple[ResultCode, str] | None:
        """Validate requested receptors are available for assignment."""
        self.logger.debug(
            "Command ID %s: Receptor IDs requested for assignment: %s",
            self.command_id,
            self.receptor_ids,
        )
        for receptor_id in self.receptor_ids:
            if self.component_manager.is_already_assigned(receptor_id):
                return (
                    ResultCode.FAILED,
                    f"Dish {receptor_id} is already allocated",
                )
            self.logger.debug(
                "Command ID: %s | Dish %s is available for assignment.",
                self.command_id,
                self.receptor_ids,
            )
        return None

    def _invoke_assign_on_subarray(self) -> Tuple[ResultCode, str]:
        """Invoke AssignResources on target TM subarray."""
        self.component_manager.log_state(
            "Device states before executing AssignResources command"
        )

        self.logger.info(
            "Command ID: %s | Invoking AssignResources command on: %s",
            self.command_id,
            self.tm_subarray_adapter,
        )

        return_codes, message_or_unique_ids = self.invoke_command(
            [self.tm_subarray_adapter],
            "Error in calling AssignResources on subarray",
            "AssignResources",
            json.dumps(self._json_argument),
        )
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

            if return_code in [ResultCode.QUEUED, ResultCode.OK]:
                self.component_manager.command_mapping[
                    self.command_id
                ] = message_or_unique_id
        return ResultCode.OK, ""

    def _build_context(self) -> MidAssignResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_assign_context(command=self)

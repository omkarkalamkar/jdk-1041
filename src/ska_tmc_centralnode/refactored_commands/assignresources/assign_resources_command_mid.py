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
    MidAssignResourcesContext,
)
from ska_tmc_centralnode.refactored_commands.assignresources.assign_resources_command import (
    AssignResources,
)


class AssignResourcesMid(AssignResources):
    """A class for CentralNode's AssignResources() command for Mid."""

    # pylint:disable=signature-differs
    def do(self, argin: str) -> Tuple[ResultCode, str]:  # type: ignore[override]
        """
        Method to invoke the AssignResources command on a Subarray.

         Args:
            argin (str): Input argument for the command

        .. literalinclude:: ../../../tests/data/command_AssignResources.json
            :language: json
            :caption: Example JSON for Assign Resources mid

        Returns:
            Tuple(ResultCode, str): Result code and message

        """
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing AssignResources command",
            self.command_id,
        )
        try:
            request = AssignResourcesPreparation(
                self.component_manager,
                self.logger,
            ).prepare_request(argin, remove_transaction_id=True)
            json_argument = request.copy_data()
        except AssignResourcesPreparationError as exception:
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

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        subarray_id = int(self.subarray_id)

        result_code, message = self.get_subarray_adapter(subarray_id)
        if result_code == ResultCode.FAILED:
            return result_code, message

        receptor_ids = plan.receptor_ids
        self.logger.debug(
            "Command ID %s: Receptor IDs requested for assignment: %s",
            self.command_id,
            receptor_ids,
        )
        for receptor_id in receptor_ids:
            if self.component_manager.is_already_assigned(receptor_id):
                return (
                    ResultCode.FAILED,
                    f"Dish {receptor_id} is already allocated",
                )
            self.logger.debug(
                "Command ID: %s | Dish %s is available for assignment.",
                self.command_id,
                receptor_ids,
            )
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
            json.dumps(json_argument),
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

    def _build_context(self) -> MidAssignResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_assign_context()

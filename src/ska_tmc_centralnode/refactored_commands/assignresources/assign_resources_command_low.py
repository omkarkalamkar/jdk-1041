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
    LowAssignResourcesContext,
)
from ska_tmc_centralnode.refactored_commands.assignresources.assign_resources_command import (
    AssignResources,
)


class AssignResourcesLow(AssignResources):
    """A class for CentralNode's AssignResources() command for low."""

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

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """
        Updates the task status for command AssignResourcesLow.

        Args:
            result: A tuple containing the result code and a message.
                The result code indicates whether the command
                succeeded or failed.
            exception (str): A string representing any exception message.
                This is used when the result indicates a failure.
                Default is an empty string.

        """
        super().update_task_status(result, exception)
        self.component_manager.subsystem_assigned_per_command_id.pop(
            self.command_id, None
        )

    # pylint:disable=signature-differs
    def do(self, argin: str) -> Tuple[ResultCode, str]:  # type: ignore[override]
        """
        Method to invoke AssignResources command on Subarray.

        Args:
            argin (str): Input argument for the command

        .. literalinclude:: ../../../tests/data/assign_resource_low.json
            :language: json
            :caption: Example JSON for Assign Resources low

        Returns:
            Tuple(ResultCode, str): tuple containing a
            return code and a string msg.
            For Example: (ResultCode.OK, "")

        :raises:
            KeyError if input argument json string contains invalid key

            ValueError if input argument json string contains invalid value

            AssertionError if  Mccs On command is not completed.
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
            ).prepare_request(argin)
            json_argument = request.copy_data()
            self.logger.debug(
                "Command ID: %s | Executing AssignResources command with "
                "arguments: %s",
                self.command_id,
                json_argument,
            )
        except AssignResourcesPreparationError as exception:
            self.logger.error(
                "Command %s: Failed to parse AssignResources JSON input: %s",
                self.command_id,
                exception,
            )
            return (
                ResultCode.FAILED,
                f"Problem in loading the JSON string: {exception}",
            )

        ctx = self._build_context()
        try:
            plan = ctx.make_strategy(self.logger).build_plan(request)
        except AssignResourcesPrepError as exception:
            return ResultCode.FAILED, str(exception)

        # apply_plan propagates subarray_id to self and subsystems to cm.
        ctx.apply_plan(plan)

        # Normalize payloads using strategy output so preparation and
        # execution stay aligned.
        json_argument["csp"] = json.loads(plan.csp_payload)
        json_argument["sdp"] = json.loads(plan.sdp_payload)
        if "mccs" in json_argument:
            json_argument["mccs"] = json.loads(plan.mccs_payload)
        if plan.telmodel:
            json_argument["telmodel"] = plan.telmodel

        assigned_subsystem: list = list(plan.subsystems)
        self.logger.debug(
            "Command %s: Subsystems assigned for subarray %s: %s",
            self.command_id,
            self.subarray_id,
            assigned_subsystem,
        )
        # INFO log for command start
        self.logger.info(
            "Command ID: %s | AssignResources started for subarray %s",
            self.command_id,
            self.subarray_id,
        )
        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        result_code, message = self.get_subarray_adapter(int(self.subarray_id))
        if result_code == ResultCode.FAILED:
            return result_code, message

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                f"Subarray Id {self.subarray_id} is not existing!",
            )

        return_codes, message_or_unique_ids = self.invoke_command(
            [self.tm_subarray_adapter],
            "Error in calling AssignResources on subarray:"
            + self.tm_subarray_adapter.dev_name,
            "AssignResources",
            json.dumps(json_argument),
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

        if (
            "mccs"
            in self.component_manager.subsystem_assigned_per_subarray[
                self.subarray_id
            ]
            and not self.is_auto_recovery_enabled
        ):
            try:
                input_mccs_master = json.loads(plan.mccs_payload)
            except Exception as exception:
                self.logger.error(
                    "Command %s: Error while preparing MCCS AssignResources "
                    "input: %s",
                    self.command_id,
                    exception,
                )
                return (
                    ResultCode.FAILED,
                    f"JSON arguments error:: {exception}",
                )

            self.component_manager.log_state(
                "Device states before executing AssignResources command"
            )
            self.logger.info(
                "Command ID: %s | Invoking AssignResources on MCCS %s",
                self.command_id,
                self.mccs_mln_adapter,
            )

            return_codes, message_or_unique_ids = self.invoke_command(
                [self.mccs_mln_adapter],
                "Error in calling AssignResources command on MCCS "
                "Master Leaf Node ",
                "AssignResources",
                json.dumps(input_mccs_master),
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
                "Command ID: %s | AssignResources completed successfully "
                "on MCCS %s",
                self.command_id,
                self.mccs_mln_adapter,
            )
            self.component_manager.subsystem_assigned_per_command_id[
                self.command_id
            ] = assigned_subsystem
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

    def create_mccs_cmd_data(self, json_argument: dict) -> dict:
        """
        Method to prepare the input json_argument required while invoking
        AssignResources() command on MCCS Master Leaf Node.

        Args:
            json_argument (dict): The string in JSON format.

        Returns:
            dict: The string in JSON format.


        """
        try:
            subarray_id = json_argument["subarray_id"]
            mccs_input = json_argument["mccs"]
            mccs_input["subarray_id"] = subarray_id
            return mccs_input
        except Exception as exception:
            raise ValueError(
                "Error while creating MCCS input json"
            ) from exception

    def _build_context(self) -> LowAssignResourcesContext:
        """Delegate context construction to the component manager."""
        return self.component_manager._get_assign_context()

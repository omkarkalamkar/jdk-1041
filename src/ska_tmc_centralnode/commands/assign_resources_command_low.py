"""
AssignResourcesLow Command class for CentralNode.
"""
import json
from typing import Tuple

from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode.utils.constants import SUB_SYSTEMS


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
        Updates the task status for command ReleaseResources

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
    def do(self, argin: str) -> Tuple[ResultCode, str]:
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
        try:
            json_argument = json.loads(argin)
            self.logger.debug(
                "Command ID: %s | Executing AssignResources command with "
                "arguments: %s",
                self.command_id,
                json_argument,
            )
        except Exception as exception:
            self.logger.error(
                "Command %s: Failed to parse AssignResources JSON input: %s",
                self.command_id,
                exception,
            )
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", exception),
            )

        if "telmodel" in json_argument:
            array_url = json_argument["telmodel"]
            self.component_manager.array_layout_url = array_url
            self.logger.debug(
                "Command ID: %s | Array layout url in input JSON: %s",
                self.command_id,
                array_url,
            )
        else:
            default_url = getattr(
                self.component_manager,
                "default_array_layout_url",
                "",
            )

            if default_url:
                if not isinstance(default_url, dict):
                    self.logger.error(
                        "Command ID:%s | Default telmodel must"
                        " be a dict got %s",
                        self.command_id,
                        type(default_url).__name__,
                    )
                    return (
                        ResultCode.FAILED,
                        "Invalid default ArrayLayout : expected a dictionary.",
                    )
                json_argument["telmodel"] = default_url
                self.component_manager.array_layout_url = default_url
                self.logger.debug(
                    "Command ID:%s | Default array layout url will be used:%s",
                    self.command_id,
                    default_url,
                )

        assigned_subsystem: list = list(
            SUB_SYSTEMS.intersection(json_argument.keys())
        )
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

        self.component_manager.subsystem_assigned_per_subarray[
            self.subarray_id
        ] = assigned_subsystem
        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        result_code, message = self.get_subarray_adapter(self.subarray_id)
        if result_code == ResultCode.FAILED:
            return result_code, message

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                ("SubArray Id %s is not existing!", self.subarray_id),
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
                input_mccs_master = self.create_mccs_cmd_data(json_argument)
            except Exception as exception:
                self.logger.error(
                    "Command %s: Error while preparing MCCS AssignResources "
                    "input: %s",
                    self.command_id,
                    exception,
                )
                return (
                    ResultCode.FAILED,
                    ("JSON arguments error:: %s", exception),
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
            raise Exception(
                "Error while creating MCCS input json"
            ) from exception

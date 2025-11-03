"""
AssignResourcesLow Command class for CentralNode.
"""
import json
from typing import Tuple

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
        **kwargs
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
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", exception),
            )

        # --------------------------------------------------------------
        # array_layout_url handling:
        # 1. if user passed it -> KEEP in json, update manager
        # 2. else -> take manager's default (if set) and inject it
        # --------------------------------------------------------------
        if "array_layout_url" in json_argument:
            array_url = json_argument["array_layout_url"]
            self.component_manager.array_layout_url = array_url
            self.logger.debug(
                "Command ID: %s | array_layout_url in argin: %s",
                self.command_id,
                array_url,
            )
        else:
            default_url = self.component_manager.default_array_layout_url
            if default_url:
                json_argument["array_layout_url"] = default_url
                self.component_manager.array_layout_url = default_url
                self.logger.debug(
                    "Command ID: %s | using default array_layout_url: %s",
                    self.command_id,
                    default_url,
                )

        assigned_subsystem: list = list(
            SUB_SYSTEMS.intersection(json_argument.keys())
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

        return_codes, message_or_unique_ids = self.send_command(
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
                return (
                    ResultCode.FAILED,
                    ("JSON arguments error:: %s", exception),
                )

            self.component_manager.log_state(
                "Device states before executing AssignResources command"
            )

            return_codes, message_or_unique_ids = self.send_command(
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
            self.component_manager.subsystem_assigned_per_command_id[
                self.command_id
            ] = assigned_subsystem
        return (ResultCode.OK, "")

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

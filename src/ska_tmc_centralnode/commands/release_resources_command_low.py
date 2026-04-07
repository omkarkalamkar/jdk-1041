"""
ReleaseResources class for CentralNode.
"""

import json
from typing import Tuple

from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode.commands.release_resources_command import (
    ReleaseResources,
)
from ska_tmc_centralnode.utils.constants import mccs_release_interface


class ReleaseResourcesLow(ReleaseResources):
    """Release Resources command class for telescope Low."""

    def __init__(
        self,
        component_manager,
        *args,
        adapter_factory=None,
        is_auto_recovery_enabled: bool = True,
        logger=None,
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
        self.component_manager.subsystem_assigned_per_subarray.pop(
            self.subarray_id, None
        )
        self.component_manager.subsystem_assigned_per_command_id.pop(
            self.command_id, None
        )
        self.component_manager.pss_beams_assigned_per_subarray.pop(
            self.subarray_id, None
        )

    # pylint:disable=signature-differs
    def do(self, argin):
        """
        Method to invoke ReleaseResources command on Subarray Node.

        Args:
            argin (str): Input argument for the command

        .. literalinclude:: ../../../tests/data/release_resource_low.json
            :language: json
            :caption: Example JSON for Release Resources low

        Returns:
            A tuple containing a return code and a string msg.
            For Example: (ResultCode.OK, "")

        :raises:
            ValueError if input argument json string contains invalid value

            KeyError if input argument json string contains invalid key

            DevFailed if the command execution or command invocation on
            SubarrayNode is not successful

        """
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Starting ReleaseResources command",
            self.command_id,
        )
        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        try:
            json_argument = json.loads(argin)
        except Exception as exception:
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", exception),
            )

        if "transaction_id" in json_argument:
            del json_argument["transaction_id"]

        result_code, message = self.get_subarray_adapter(self.subarray_id)
        if result_code == ResultCode.FAILED:
            return result_code, message

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                ("Subarray Id %s is not existing!", self.subarray_id),
            )

        if json_argument["release_all"] is True:
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
                    input_mccs_master = self.create_mccs_input_data(
                        json_argument
                    )
                except Exception as exception:
                    return (
                        ResultCode.FAILED,
                        ("Error in MCCS JSON argument: %s", exception),
                    )
                self.logger.info(
                    "Command ID: %s | Invoking ReleaseAllResources on MCCS %s",
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
            "Command ID: %s |  Release Resources "
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

    def release_all_resources_mccs(
        self, adapter, argin
    ) -> Tuple[list[ResultCode], list[str]]:
        """
        Releases all resources mccs

        Args:
            adapter: Adapter

        Returns:
            Tuple(list, list): Tuple of list of ResulCodes
            and lists of messages.

        """
        return self.invoke_command(
            [adapter],
            f"Error in calling ReleaseAllResources() on {adapter.dev_name}"
            + "device",
            "ReleaseAllResources",
            json.dumps(argin),
        )

    def create_mccs_input_data(self, json_argument: dict) -> dict:
        """
        Creates mccs input strings

        Args:
            json_argument (dict): Json argument

        Returns:
            dict: MCCS input data json

        """
        try:
            if "interface" in json_argument:
                del json_argument["interface"]
            json_argument["interface"] = mccs_release_interface
            return json_argument
        except Exception as exception:
            raise Exception(
                "Error while creating MCCS input json"
            ) from exception

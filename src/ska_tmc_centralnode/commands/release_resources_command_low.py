"""
ReleaseResources class for CentralNode.
"""

import json
from typing import Tuple

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

        if "subarray_id" not in json_argument:
            return (
                ResultCode.FAILED,
                "subarray_id key is not present in the input json argument.",
            )

        subarray_id = json_argument["subarray_id"]

        for adapter in self.subarray_adapters:
            if str(subarray_id) in adapter.dev_name:
                self.subarray_adapter = adapter
                self.component_manager.subarray_devname = adapter.dev_name

        if self.subarray_adapter is None:
            return (
                ResultCode.FAILED,
                f"Subarray Id {subarray_id} doesn't exit!",
            )

        if json_argument["release_all"] is True:
            (
                return_codes,
                message_or_unique_ids,
            ) = self.release_all_resources(self.subarray_adapter)
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
                "mccs" in self.component_manager.subsystems_to_config
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
        return (ResultCode.OK, "")

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
        return self.send_command(
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

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


class ReleaseResourcesMid(ReleaseResources):
    """Release Resources command class for Mid."""

    # pylint:disable=signature-differs
    def do(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke ReleaseResources command on Subarray.

        Args:
            argin (str): Input argument for the command

        .. literalinclude:: ../../../tests/data/command_ReleaseResources.json
            :language: json
            :caption: Example JSON for Release Resources mid

        Returns:
            A tuple containing a return code and a string msg.
            For Example: (ResultCode.OK, "")

        """
        ret_code, msg = super().do(argin)
        if ret_code == ResultCode.FAILED:
            return ret_code, msg
        json_argument = json.loads(argin)
        if "transaction_id" in json_argument:
            del json_argument["transaction_id"]
        if json_argument.get("release_all") is True:
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
                    )  # even if command is rejected by subarraynode ,
                    # it will be resultcode failed for centralnode
                if return_code in [ResultCode.QUEUED, ResultCode.OK]:
                    self.component_manager.command_mapping[
                        self.command_id
                    ] = message_or_unique_id
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
        return (
            ResultCode.FAILED,
            "Partial release resources not supported!",
        )

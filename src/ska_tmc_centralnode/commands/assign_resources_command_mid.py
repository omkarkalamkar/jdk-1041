"""AssignResourcesLow Command class for CentralNode.
"""
import json
from typing import Tuple

from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)


class AssignResourcesMid(AssignResources):
    """A class for CentralNode's AssignResources() command for Mid."""

    # pylint:disable=signature-differs
    def do(self, argin: str) -> Tuple[ResultCode, str]:
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
        try:
            self.logger.debug(
                "Command ID: %s | Loading the  AssignResource JSON string",
                self.command_id,
            )
            json_argument = json.loads(argin)
        except Exception as e:
            return (
                ResultCode.FAILED,
                f"Problem in loading the JSON string: {e}",
            )

        if "transaction_id" in json_argument:
            del json_argument["transaction_id"]

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        subarrayID = int(json_argument["subarray_id"])

        result_code, message = self.get_subarray_adapter(subarrayID)
        if result_code == ResultCode.FAILED:
            return result_code, message

        receptor_ids = json_argument["dish"]["receptor_ids"]
        self.logger.debug(
            "Command ID: %s | Receptor IDs are: %s",
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

        return_codes, message_or_unique_ids = self.send_command(
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
            "Command ID: %s | Resources assigned successfully on: %s",
            self.command_id,
            self.tm_subarray_adapter,
        )

        return (ResultCode.OK, "")

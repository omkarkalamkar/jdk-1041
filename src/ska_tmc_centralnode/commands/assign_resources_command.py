"""
AssignResources Command class for CentralNode.
"""

import json
import time
from typing import Optional, Tuple

from ska_ser_skuid.client import SkuidClient
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import AdapterFactory, TimeoutCallback
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_centralnode.commands.central_node_command import (
    AssignReleaseResources,
)


class AssignResources(AssignReleaseResources):
    """
    A class for CentralNode's AssignResources() command.

    Assigns resources to a given subarray. It accepts the subarray ID,
    receptor ID list, and SDP block in JSON string format.

    Upon successful execution, the 'receptor_ids' attribute of the given
    subarray is populated with the given receptors.

    Checking for duplicate allocation of resources is done.
    If already allocated, it will throw an error message regarding the prior
    existence of the resource.
    """

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        skuid=SkuidClient(
            "ska-ser-skuid-test-svc.ska-tmc-centralnode.svc.techops.internal"
            + ".skao.int:9870"
        ),
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self.tm_subarray_adapter: Optional[AdapterFactory] = None
        self._skuid: SkuidClient = skuid
        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)

    @timeout_tracker
    @error_propagation_tracker(
        "get_subarray_obsstate", [ObsState.RESOURCING, ObsState.IDLE]
    )
    def assign_resources(
        self,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        """
        This is a long running command method for AssignResources command.

        It executes the do hook and invokes the AssignResources command on
        lower-level devices.

        Args:
            argin (str): Input argument for the command.

        Returns:
            Tuple(ResultCode, str): Result code and message.

        """
        return self.do(argin)

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """
        Updates the task status for a command.

        Args:
            result: A tuple containing the result code and a message.
                The result code indicates whether the command
                succeeded or failed.
            exception (str): A string representing any exception message.
                This is used when the result indicates a failure.
                Default is an empty string.

        """
        if result[0] == ResultCode.FAILED:
            self.task_callback(
                result=result, status=TaskStatus.COMPLETED, exception=exception
            )
            self.component_manager.subarray_devname = ""
        else:
            self.task_callback(result=result, status=TaskStatus.COMPLETED)
        self.component_manager.command_in_progress = ""
        if self.component_manager.command_mapping.get(
            self.component_manager.command_id
        ):
            self.component_manager.command_mapping.pop(
                self.component_manager.command_id
            )

    # pylint:disable=signature-differs
    def do_mid(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke the AssignResources command on a Subarray.

        Args:
            argin (str): Input argument for the command

        .. literalinclude:: ../../tests/data/command_AssignResources.json
            :language: json
            :caption: Example JSON for Assign Resources mid

        Returns:
            Tuple(ResultCode, str): Result code and message

        """
        try:
            self.logger.debug(
                "Command ID: %s | Loading the  AssignResource JSON string",
                self.component_manager.command_id,
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
            self.component_manager.command_id,
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
                self.component_manager.command_id,
                receptor_ids,
            )
        self.component_manager.log_state(
            "Device states before executing AssignResources command"
        )

        self.logger.info(
            "Command ID: %s | Invoking AssignResources command on: %s",
            self.component_manager.command_id,
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
                    self.component_manager.command_id
                ] = message_or_unique_id

        self.logger.info(
            "Command ID: %s | Resources assigned successfully on: %s",
            self.component_manager.command_id,
            self.tm_subarray_adapter,
        )

        return (ResultCode.OK, "")

    def update_resource_config_file(
        self, json_argument: dict, sdp_id: str
    ) -> None:
        """
        Updates the resource configuration file.

        This method updates the resource configuration file with unique
        identifiers for execution blocks and processing blocks.
        It fetches unique IDs using the `skuid` service and updates the
        corresponding entries in the provided JSON argument.

        Args:
            json_argument (dict): A dictionary containing the
                JSON argument for the update. This dictionary
                should have a specific structure with keys
                for 'sdp', 'execution_block', and 'processing_blocks'.
            sdp_id (str):
                A string representing the ID for the resource
                configuration file.

        Raises:
            Exception: If the 'processing_blocks' key is not present
                in the input JSON argument.

        """
        # New type of id "eb_id" is used to distinguish between real
        # SB and id used during testing
        unique_id = self._skuid.fetch_skuid("eb")
        json_argument["sdp"]["execution_block"][sdp_id] = unique_id
        if "processing_blocks" in json_argument["sdp"]:
            for i in range(len(json_argument["sdp"]["processing_blocks"])):
                pb_id = self._skuid.fetch_skuid("pb")
                json_argument["sdp"]["processing_blocks"][i]["pb_id"] = pb_id
                if (
                    "dependencies"
                    in json_argument["sdp"]["processing_blocks"][i]
                ):
                    if i == 0:
                        json_argument["sdp"]["processing_blocks"][i][
                            "dependencies"
                        ][0]["pb_id"] = json_argument["sdp"][
                            "processing_blocks"
                        ][
                            i
                        ][
                            "pb_id"
                        ]
                    else:
                        json_argument["sdp"]["processing_blocks"][i][
                            "dependencies"
                        ][0]["pb_id"] = json_argument["sdp"][
                            "processing_blocks"
                        ][
                            i - 1
                        ][
                            "pb_id"
                        ]
        else:
            raise Exception(
                "processing_blocks key not present in the input json argument"
            )

    # pylint:disable=signature-differs
    def do_low(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke AssignResources command on Subarray.

        Args:
            argin (str): Input argument for the command

        .. literalinclude:: ../../tests/data/command_assign_resource_low.json
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
                "Command ID: %s | Executing AssignResources "
                + "command with arguments: %s",
                self.component_manager.command_id,
                json_argument,
            )
        except Exception as exception:
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", exception),
            )

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        subarrayID = int(json_argument["subarray_id"])

        result_code, message = self.get_subarray_adapter(subarrayID)
        if result_code == ResultCode.FAILED:
            return result_code, message

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                ("SubArray Id %s is not existing!", subarrayID),
            )

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
        for return_codes, message_or_unique_ids in [
            self.send_command(
                [self.tm_subarray_adapter],
                "Error in calling AssignResources on subarray:"
                + self.tm_subarray_adapter.dev_name,
                "AssignResources",
                json.dumps(json_argument),
            ),
            self.send_command(
                [self.mccs_mln_adapter],
                "Error in calling AssignResources command"
                + " on MCCS Master Leaf Node ",
                "AssignResources",
                json.dumps(input_mccs_master),
            ),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                    return (
                        ResultCode.FAILED,
                        message_or_unique_id,
                    )
                if return_code in [ResultCode.QUEUED, ResultCode.OK]:
                    if self.component_manager.command_mapping.get(
                        self.component_manager.command_id
                    ):
                        self.logger.debug(
                            "Command ID : %s |"
                            + "Adding the ID %s to the command mapping"
                            + "dictionary under command_id: %s",
                            self.component_manager.command_id,
                            message_or_unique_id,
                            self.component_manager.command_id,
                        )
                        self.component_manager.command_mapping[
                            self.component_manager.command_id
                        ].append(message_or_unique_id)
                    else:
                        self.logger.debug(
                            "Command ID: %s |"
                            + "Creating a command mapping dictionary for id:"
                            + "%s, with unique_id: %s",
                            self.component_manager.command_id,
                            self.component_manager.command_id,
                            message_or_unique_id,
                        )
                        self.component_manager.command_mapping[
                            self.component_manager.command_id
                        ] = [message_or_unique_id]

        return (ResultCode.OK, "")

    def _validate_and_update_resource_config(
        self, json_argument: dict
    ) -> Tuple[bool, str]:
        """
        Validate and update the resource configuration.

        This method validates if the 'eb_id' is present in the SDP schema
        within the provided JSON argument. If the 'eb_id' is not
        present, it fetches the appropriate IDs and updates the resource
        configuration file accordingly.

        Args:
            json_argument (dict): A dictionary representing
                the low-level JSON configuration for the resource.

        Returns:
            Tuple(bool, str): A tuple where the first element
            is a boolean indicating the success
            of the validation and update process, and the second
            element is a string containing an error message if the
            process failed.

        Raises:
            Exception: If an error occurs while updating
            the SDP schema, it returns a tuple
            with False and the error message.

        """
        try:
            if (
                json_argument["sdp"].get("execution_block")
                and not json_argument["sdp"]["execution_block"]["eb_id"]
            ):
                sdp_keys = list(json_argument["sdp"]["execution_block"].keys())
                sdp_values = list(
                    json_argument["sdp"]["execution_block"].values()
                )
                sdp_id = sdp_keys[sdp_values.index("")]
                self.update_resource_config_file(json_argument, sdp_id)
            return True, ""
        except Exception as exception:
            return False, f"Error while updating SDP schema: {exception}"

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

    def get_subarray_adapter(self, subarray_id: int) -> Tuple[ResultCode, str]:
        """
        Method for obtaining the adapter for a subarray.

        Args:
            subarray_id (int): An integer representing
                the subarray ID.

        Returns:
            A tuple containing a ResultCode
            enum value and a string message.

        """
        for adapter in self.subarray_adapters:
            if str(subarray_id) in adapter.dev_name:
                self.tm_subarray_adapter = adapter
                self.component_manager.subarray_devname = adapter.dev_name

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                f"SubArray Id {subarray_id} is not existing!",
            )

        return ResultCode.OK, ""

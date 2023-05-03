"""
ReleaseResources class for CentralNode.
"""
import json
import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_centralnode.commands.abstract_command import (
    AbstractAssignReleaseResources,
)


class ReleaseResources(AbstractAssignReleaseResources):
    """
    A class for CentralNode's ReleaseResources() command.

    Release all the resources assigned to the given Subarray. It accepts the subarray id, releaseALL flag and
    receptorIDList in JSON string format. When the releaseALL flag is True, ReleaseAllResources command
    is invoked on the respective SubarrayNode. In this case, the receptorIDList tag is empty as all
    the resources of the Subarray are to be released.
    When releaseALL is False, ReleaseResources will be invoked on the SubarrayNode and the resources provided
    in receptorIDList tag, are to be released from the Subarray. The selective release of the resources when
    releaseALL Flag is False is not yet supported.
    """

    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self.subarray_adapters = []
        self.my_subarray_adapter = None

    def release_resources(
        self,
        argin,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):

        """This is a long running method for ReleaseResources command, it executes do hook,
        invokes ReleaseResources command on lower level devices.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)

        ret_code, message = self.do(argin=json.dumps(argin))
        self.logger.info(message)
        if ret_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.FAILED,
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.OK,
            )

    def do_mid(self, argin):
        """
        Method to invoke ReleaseResources command on Subarray.

        :param argin: The string in JSON format. The JSON contains following values:

            subarray_id:
                DevShort. Mandatory.

            release_all:
                Boolean(True or False). Mandatory. True when all the resources to be released from Subarray.

            receptor_ids:
                DevVarStringArray. Empty when release_all tag is True.

            Example:
                {
                    "interface": "https://schema.skao.int/ska-tmc-releaseresources/2.0",
                    "transaction_id": "txn-....-00001",
                    "subarray_id": 1,
                    "release_all": true,
                    "receptor_ids": [
                    ]
                }

        :return: None
        """
        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        try:
            if type(argin) != dict:
                jsonArgument = json.loads(argin)
            else:
                jsonArgument = argin
        except Exception as e:
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
            )

        if "transaction_id" in jsonArgument:
            del jsonArgument["transaction_id"]

        if "subarray_id" not in jsonArgument:
            return (
                ResultCode.FAILED,
                "subarray_id key is not present in the input json argument.",
            )

        subarray_id = jsonArgument["subarray_id"]

        for adapter in self.subarray_adapters:
            if str(subarray_id) in adapter.dev_name:
                self.subarray_adapter = adapter

        if self.subarray_adapter is None:
            return (
                ResultCode.FAILED,
                ("Subarray id %s is not existing!", subarray_id),
            )
        if jsonArgument["release_all"] is True:
            ret_code, message = self.release_all_resources(
                self.subarray_adapter
            )
            if ret_code == ResultCode.FAILED:
                return ret_code, message

            return (ResultCode.OK, "")
        else:
            return (
                ResultCode.FAILED,
                "Partial release resources not supported!",
            )

    def _validate_mid_json(self, json_argument: dict, req_keys: list):
        """To validate the low json for release resources command before erterning the queue
        Args:
            json_argument (dict): Json Argument
            req_keys (list): Required key list to check in json argument
        """
        json_keys = json_argument.keys()
        for key in req_keys:
            if key not in json_keys:
                return (
                    False,
                    f"{key} key is not present in the input json argument.",
                )
        return (
            True,
            "The json argument has all the required keys. Validation successful.",
        )

    def do_low(self, argin):
        """
        Method to invoke ReleaseResources command on Subarray Node.

        :param argin: The string in JSON format. The JSON contains following values:

            subarray_id:
                DevShort. Mandatory.

            release_all:
                Boolean(True or False). Mandatory. True when all the resources to be released from Subarray.

            Example:
                {"interface":"https://schema.skao.int/ska-low-tmc-releaseresources/2.0","transaction_id":"txn-....-00001","subarray_id":1,"release_all":true}
            Note: From Jive, enter input as:
                {"interface":"https://schema.skao.int/ska-low-tmc-releaseresources/2.0","transaction_id":"txn-....-00001","subarray_id":1,"release_all":true}
                without any space.
        return:
            None

        raises:
            ValueError if input argument json string contains invalid value

            KeyError if input argument json string contains invalid key

            DevFailed if the command execution or command invocation on SubarrayNode is not successful

        """
        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        try:
            if type(argin) != dict:
                jsonArgument = json.loads(argin)
            else:
                jsonArgument = argin
        except Exception as e:
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
            )

        if "transaction_id" in jsonArgument:
            del jsonArgument["transaction_id"]

        if "subarray_id" not in jsonArgument:
            return (
                ResultCode.FAILED,
                "subarray_id key is not present in the input json argument.",
            )

        subarray_id = jsonArgument["subarray_id"]

        for adapter in self.subarray_adapters:
            if str(subarray_id) in adapter.dev_name:
                self.subarray_adapter = adapter

        if self.subarray_adapter is None:
            return (
                ResultCode.FAILED,
                ("Subarray id %s is not existing!", subarray_id),
            )

        self.logger.info(jsonArgument)

        if jsonArgument["release_all"] is True:
            ret_code, message = self.release_all_resources(
                self.subarray_adapter
            )
            if ret_code == ResultCode.FAILED:
                return ret_code, message
            return (ResultCode.OK, "")

        # TODO Uncomment below code during integration of MCCS
        # Invoke ReleaseAllResources on MCCS Master Leaf Node
        # Send updated input string with inteface key to MCCS Master for ReleaseResource Command
        # jsonArgument[
        #     "interface"
        # ] = "https://schema.skao.int/ska-low-mccs-releaseresources/1.0"
        # if "transaction_id" in jsonArgument:
        #     del jsonArgument["transaction_id"]

        #     ret_code, message = self.release_resources_mccs(
        #         json.dumps(jsonArgument)
        #     )
        #     if ret_code == ResultCode.FAILED:
        #         return ret_code, message

    def release_all_resources(self, adapter):
        return self.send_command(
            [adapter],
            "Error in calling ReleaseAllResources() on TMC Device",
            "ReleaseAllResources",
        )

    def release_resources_mccs(self, arg):
        return self.send_command(
            [self.tm_leaf_mccs_master_adapter],
            "Error in calling ReleaseResources() on TMC Device",
            "ReleaseResources",
            arg,
        )

    def _validate_low_json(self, json_argument: dict, req_keys: list):
        """To validate the low json for release resources command before erterning the queue
        Args:
            json_argument (dict): Json Argument
            req_keys (list): Required key list to check in json argument
        """
        json_keys = json_argument.keys()
        for key in req_keys:
            if key not in json_keys:
                return (
                    False,
                    f"{key} key is not present in the input json argument.",
                )
        return (
            True,
            "The json argument has all the required keys. Validation successful.",
        )

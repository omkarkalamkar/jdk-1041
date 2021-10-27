"""
ReleaseResources class for CentralNode.
"""
import json

from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode_mid.commands.abstract_command import (
    AbstractAssignReleaseResources,
)
from ska_tmc_centralnode_mid.manager.adapters import AdapterFactory


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
        target,
        pop_state_model,
        adapter_factory=AdapterFactory(),
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(target, args, logger, kwargs)
        self.op_state_model = pop_state_model
        self._adapter_factory = adapter_factory
        self.tm_dish_adapters = []
        self.tm_subarray_adapters = []

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

            Note: From Jive, enter input as: {"interface":"https://schema.skao.int/ska-tmc-releaseresources/1.0",
            "subarray_id":1,"release_all":true,"receptor_ids":[]}

        :return: None
        """
        ret_code, message = self.init_adapters_mid()
        if ret_code == ResultCode.FAILED:
            return ret_code, message
        try:
            jsonArgument = json.loads(argin)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
            )

        if "transaction_id" not in jsonArgument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "transaction_id key is not present in the input json argument.",
            )

        if "transaction_id" in jsonArgument:
            del jsonArgument["transaction_id"]

        if "subarray_id" not in jsonArgument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "subarray_id key is not present in the input json argument.",
            )

        subarrayID = jsonArgument["subarray_id"]

        my_subarray_adapter = None
        for adapter in self.tm_subarray_adapters:
            if str(subarrayID) in adapter.dev_name:
                my_subarray_adapter = adapter

        if my_subarray_adapter is None:
            return self.generate_command_result(
                ResultCode.FAILED,
                ("SubArray Id %s is not existing!", subarrayID),
            )

        if jsonArgument["release_all"]:
            # Invoke "ReleaseAllResources" on SubarrayNode
            try:
                return_val = my_subarray_adapter.ReleaseAllResources()
                self.logger.info(
                    "Command result from Subarray: %s", return_val
                )
                # Leave the monitoring loop to do the updates on the resources!
                # component_manager.add_command_execution("ReleaseResources", ResultCode.OK, "")
                return (ResultCode.OK, "")
            except Exception as e:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    (
                        "Error in calling ReleaseAllResources on subarray %s: %s",
                        my_subarray_adapter.dev_name,
                        e,
                    ),
                )
        else:
            return (
                ResultCode.FAILED,
                "Partial release resources not supported!",
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

        ret_code, message = self.init_adapters_low()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        try:
            json_argument = json.loads(argin)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
            )

        if "subarray_id" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "subarray_id key is not present in the input json argument.",
            )

        if "transaction_id" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "transaction_id key is not present in the input json argument.",
            )

        subarrayID = int(json_argument["subarray_id"])

        my_subarray_adapter = None
        for adapter in self.tm_subarray_adapters:
            if str(subarrayID) in adapter.dev_name:
                my_subarray_adapter = adapter

        if my_subarray_adapter is None:
            return self.generate_command_result(
                ResultCode.FAILED,
                ("SubArray Id %s is not existing!", subarrayID),
            )

        if json_argument["release_all"] is True:
            try:
                # Invoke ReleaseAllResources on SubarrayNode
                my_subarray_adapter.ReleaseAllResources()
            except Exception as e:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    (
                        "Error in calling ReleaseResources on subarray %s: %s",
                        my_subarray_adapter.dev_name,
                        e,
                    ),
                )
            # Invoke ReleaseAllResources on MCCS Master Leaf Node
            # Send updated input string with inteface key to MCCS Master for ReleaseResource Command
            json_argument[
                "interface"
            ] = "https://schema.skao.int/ska-low-mccs-releaseresources/1.0"
            if "transaction_id" in json_argument:
                del json_argument["transaction_id"]
                try:
                    self.tm_leaf_mccs_master_adapter.ReleaseResources(
                        json.dumps(json_argument)
                    )
                except Exception as e:
                    return self.generate_command_result(
                        ResultCode.FAILED,
                        f"Error in calling ReleaseResources command on TM MCCS Master Leaf {self.tm_leaf_mccs_master_adapter.dev_name}: {e}",
                    )

            return (ResultCode.OK, "")

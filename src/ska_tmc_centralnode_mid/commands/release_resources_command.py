"""
ReleaseResources class for CentralNode.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import json
import ast

import tango
from tango import DevState, DevFailed

# Additional import
from ska_tmc_centralnode_mid.manager.adapters import AdapterFactory
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.commands.abstract_command import AbstractAssignReleaseResources

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

    def __init__(self, target, pop_state_model, adapter_factory = AdapterFactory(),
                *args, logger=None, **kwargs):
        super().__init__(target, args, logger, kwargs)
        self.op_state_model = pop_state_model
        self._adapter_factory = adapter_factory
        self.tm_dish_adapters = []
        self.tm_subarray_adapters = []

    def do(self, argin):
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

        return:
            A tuple containing a return code and a string in josn format on successful release
            of all the resources. The JSON string contains following values:

            release_all:
                Boolean(True or False). If True, all the resources are successfully released from the
                Subarray.

            receptor_ids:
                DevVarStringArray. If release_all is True, receptor_ids is empty. Else list returns
                resources (device names) that are noe released from the subarray.

            Example:
                argout =
                    {
                    "interface": "https://schema.skao.int/ska-tmc-releaseresources/2.0",
                    "subarray_id": 1,
                    "release_all": true,
                    "receptor_ids": [       
                    ]
                    }

        return:
            None

        """
        component_manager = self.target
        ret_code, message = self.init_adapters("ReleaseResources", component_manager)
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        jsonArgument = json.loads(argin)
        if not 'transaction_id' in jsonArgument:
            return self.generate_command_result(ResultCode.FAILED, "transaction_id in not present in the input json argument!")

        if 'transaction_id' in jsonArgument:
            del jsonArgument["transaction_id"]

        if not 'subarray_id' in jsonArgument:
            return self.generate_command_result(ResultCode.FAILED, "subarray_id in not present in the input json argument!")

        subarrayID = jsonArgument["subarray_id"]

        my_subarray_adapter = None
        for adapter in self.tm_subarray_adapters:
            if str(subarrayID) in adapter.dev_name:
                my_subarray_adapter = adapter

        if my_subarray_adapter is None:
            return self.generate_command_result(ResultCode.FAILED, ("SubArray Id %s is not existing!", subarrayID))

        if jsonArgument["release_all"] == True:
            # Invoke "ReleaseAllResources" on SubarrayNode
            try:
                return_val = my_subarray_adapter.ReleaseAllResources()
                self.logger.info("Command result from Subarray: %s", return_val)
                # Leave the monitoring loop to do the updates on the resources!
                # component_manager.add_command_execution("ReleaseResources", ResultCode.OK, "")
                return (ResultCode.OK, "")
            except Exception as e:
                return self.generate_command_result(ResultCode.FAILED, ("Error in calling ReleaseAllResources on subarray %s: %s", my_subarray_adapter.dev_name, e))
        else:
            return (ResultCode.FAILED, "Partial release resources not supported!")

        
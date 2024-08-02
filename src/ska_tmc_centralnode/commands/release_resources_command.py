"""
ReleaseResources class for CentralNode.
"""
import json
from typing import Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import AdapterFactory

from ska_tmc_centralnode.commands.central_node_command import (
    AssignReleaseResources,
)
from ska_tmc_centralnode.utils.constants import mccs_release_interface


class ReleaseResources(AssignReleaseResources):
    """
    A class for CentralNode's ReleaseResources() command.

    Release all the resources assigned to the given Subarray. It accepts the
    subarray id, releaseALL flag and receptorIDList in JSON string format.
    When the releaseALL flag is True, ReleaseAllResources command
    is invoked on the respective SubarrayNode. In this case,the receptorIDList
    tag is empty as all the resources of the Subarray are to be released.
    When releaseALL is False, ReleaseResources will be invoked on
    the SubarrayNode and the resources provided in receptorIDList tag, are to
    be released from the Subarray. The selective release of the resources when
    releaseALL Flag is False is not yet supported.
    """

    def __init__(
        self,
        component_manager,
        adapter_factory: Optional[AdapterFactory] = None,
        *args,
        logger=None,
        **kwargs,
    ):
        # pylint:disable=keyword-arg-before-vararg
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self.my_subarray_adapter = None
        self.subarray_adapter = None

    def release_resources(
        self,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        """This is a long running method for ReleaseResources command

        :param argin: Input argument for the command
        :type argin: `str`
        :returns: Result code and message
        :rtype: `Tuple[ResultCode, str]`
        """
        return self.do(argin=argin)

    # pylint:disable=signature-differs
    def do_mid(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke ReleaseResources command on Subarray.

        :param argin: DevString

        Example:

        .. code-block::

            {"interface":
            "https://schema.skao.int/ska-tmc-releaseresources/2.0",
            "transaction_id": "txn-....-00001",
            "subarray_id": 1,
            "release_all": true,
            "receptor_ids": []
            }

            :return: A tuple containing a return code and a string msg.
                For Example:
                (ResultCode.OK, "")
        """
        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        try:
            json_argument = json.loads(argin)
        except Exception as exception:
            return (
                ResultCode.FAILED,
                f"Problem in loading the JSON string: {exception}",
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
            return_codes, message_or_unique_ids = self.release_all_resources(
                self.subarray_adapter
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
                        self.component_manager.command_id
                    ] = message_or_unique_id
            return (ResultCode.OK, "")
        return (
            ResultCode.FAILED,
            "Partial release resources not supported!",
        )

    # pylint:disable=signature-differs
    def do_low(self, argin):
        """
        Method to invoke ReleaseResources command on Subarray Node.

        :param: argin
        :type: DevString

        Example:

        .. code-block::

            {"interface":
            "https://schema.skao.int/ska-low-tmc-releaseresources/2.0",
            "transaction_id":"txn-....-00001","subarray_id":1,
            "release_all":true}

        :return:
            A tuple containing a return code and a string msg.
            For Example:
            (ResultCode.OK, "")

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
        try:
            input_mccs_master = self.create_mccs_input_data(json_argument)
        except Exception as exception:
            return (
                ResultCode.FAILED,
                ("Errors in input json argument: %s", exception),
            )
        if json_argument["release_all"] is True:
            for return_codes, message_or_unique_ids in (
                self.release_all_resources(self.subarray_adapter),
                self.release_all_resources_mccs(
                    self.mccs_mln_adapter, input_mccs_master
                ),
            ):
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
                        if self.component_manager.command_mapping.get(
                            self.component_manager.command_id
                        ):
                            self.component_manager.command_mapping[
                                self.component_manager.command_id
                            ].append(message_or_unique_id)
                        else:
                            self.component_manager.command_mapping[
                                self.component_manager.command_id
                            ] = [message_or_unique_id]
        return (ResultCode.OK, "")

    def release_all_resources(self, adapter):
        """Releases all resources"""
        return self.send_command(
            [adapter],
            f"Error in calling ReleaseAllResources() on {adapter.dev_name}"
            + " device",
            "ReleaseAllResources",
        )

    def release_all_resources_mccs(self, adapter, argin):
        """Releases all resources mccs"""
        return self.send_command(
            [adapter],
            f"Error in calling ReleaseAllResources() on {adapter.dev_name}"
            + "device",
            "ReleaseAllResources",
            json.dumps(argin),
        )

    def create_mccs_input_data(self, json_argument: dict) -> dict:
        """Creates mccs input strings"""
        try:
            if "interface" in json_argument:
                del json_argument["interface"]
            json_argument["interface"] = mccs_release_interface
            return json_argument
        except Exception as exception:
            raise Exception(
                "Error while creating MCCS input json"
            ) from exception

    def update_task_status(self):
        """Updates task status implemented to"""

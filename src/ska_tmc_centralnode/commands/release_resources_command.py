"""
ReleaseResources class for CentralNode.
"""
import json
import threading
from logging import Logger
from typing import Callable, Optional, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
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
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """This is a long running method for ReleaseResources command,
        it executes do hook, invokes ReleaseResources command on lower
        level devices.

        :param: logger
        :type: logging.Logger
        :param: task_callback which Update task state, defaults to None
        :type: Callable, optional
        :param: task_abort_event which Check for abort, defaults to None
        :type: Event, Optional
        """
        # Indicate that the task has started
        self.task_callback = task_callback
        self.set_command_id(__class__.__name__)
        task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.command_in_progress = "ReleaseResources"
        self.component_manager.command_result = ResultCode.STARTED
        self.component_manager.start_timer(
            self.timeout_id,
            self.component_manager.command_timeout,
            self.timeout_callback,
        )

        result_code, message = self.do(argin=argin)
        self.logger.info(
            "ReleaseResources command execution result: %s, message: %s",
            result_code,
            message,
        )
        if result_code == ResultCode.FAILED:
            self.update_task_status((result_code, message), message)
            self.component_manager.stop_timer()
            self.component_manager.command_mapping.pop(
                self.component_manager.command_id
            )
        else:
            self.start_tracker_thread(
                "get_subarray_obsstate",
                [ObsState.RESOURCING, ObsState.EMPTY],
                task_abort_event,
                timeout_id=self.timeout_id,
                timeout_callback=self.timeout_callback,
                command_id=self.component_manager.command_id,
                lrcr_callback=(
                    self.component_manager.long_running_result_callback
                ),
            )

    def update_task_status(self, result: ResultCode, exception: str = ""):
        """Updates the task status for command"""
        if result[0] == ResultCode.FAILED:
            self.task_callback(
                result=result,
                status=TaskStatus.COMPLETED,
                exception=exception,
            )
            self.component_manager.subarray_devname = ""
        else:
            self.task_callback(result=result, status=TaskStatus.COMPLETED)
        if self.component_manager.command_mapping.get(
            self.component_manager.command_id
        ):
            self.component_manager.command_mapping.pop(
                self.component_manager.command_id
            )
        self.component_manager.command_in_progress = ""

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
        except Exception as e:
            return (
                ResultCode.FAILED,
                f"Problem in loading the JSON string: {e}",
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
        except Exception as e:
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
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
        except Exception as e:
            return (
                ResultCode.FAILED,
                ("Errors in input json argument: %s", e),
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
        except Exception as e:
            raise Exception("Error while creating MCCS input json") from e

    def _validate_low_json(self, json_argument: dict, req_keys: list):
        """To validate the low json for release resources command before
        erterning the queue

        :param: json_argument
        :type: A dictionary containing Json Argument
        :param: req_keys
        :type: A Lis tof Required key list to check in json_argument
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
            "The json argument has all the required keys. Validation"
            + " successful.",
        )

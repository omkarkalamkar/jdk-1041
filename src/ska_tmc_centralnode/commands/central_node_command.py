"""Command class for central node"""

# pylint:disable =abstract-method
import logging
import operator
import threading
import time
from typing import Any, List, Optional, Tuple, Union

from ska_control_model import TaskStatus
from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.faults import CommandError, ResultCodeError
from ska_tango_base.long_running_commands.api import invoke_lrc
from ska_tmc_common import TimeoutCallback
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.tmc_command import TMCCommand

from ska_tmc_centralnode.model.input import InputParameterMid

configure_logging()
LOGGER = logging.getLogger(__name__)


def task_callback_default(
    status: Union[TaskStatus, None] = None,
    progress: Union[int, None] = None,
    result: Any = None,
    exception: Union[Exception, None] = None,
) -> None:
    """
    Default method if the taskcallback is not passed

    :param status: status of the task.
    :param progress: progress of the task.
    :param result: result of the task.
    :param exception: an exception raised from the task.
    """
    LOGGER.warning(
        "This is default task callback."
        + "There is no action taken under this callback."
        + "Please provide task callback."
    )
    LOGGER.debug(
        "long running command status: %s, progress: %s ,result:%s ,"
        + "exception %s",
        status,
        progress,
        result,
        exception,
    )


# pylint:disable=keyword-arg-before-vararg
class CentralNodeCommand(TMCCommand):
    """Central node command class"""

    def __init__(
        self,
        component_manager,
        *args,
        logger: logging.Logger = LOGGER,
        **kwargs,
    ):
        super().__init__(component_manager, logger, *args, **kwargs)
        self.timeout_id: str = f"{time.time()}_{self.__class__.__name__}"
        self.timeout_callback: TimeoutCallback = TimeoutCallback(
            self.timeout_id, self.logger
        )
        self.task_callback: TaskCallbackType = task_callback_default
        self.mccs_mln_adapter = None
        self.command_subs_list = []
        self.command_results = {}
        self.command_device_id_map = {}
        self.task_abort_event = threading.Event()

    def init_adapters(self) -> Tuple[ResultCode, str]:
        """Initialises adapters for central node command class"""
        if isinstance(
            self.component_manager.input_parameter, InputParameterMid
        ):
            result, message = self.init_adapters_mid()
        else:
            result, message = self.init_adapters_low()

        return result, message

    def do(self, argin: Optional[str] = None) -> ResultCode:
        """Do method for central node command class"""
        if isinstance(
            self.component_manager.input_parameter, InputParameterMid
        ):
            result = self.do_mid(argin)
        else:
            result = self.do_low(argin)

        return result

    def invoke_command(
        self,
        adapters: List,
        err_msg: str,
        command_name: str,
        argin: Optional[str] = None,
        callback=None,
    ) -> Tuple[List[ResultCode | Any], List[str | Any]]:
        """
        Invokes command on adapters

        Args:
            adapters: list of the adapters.
            command_caller: command caller.
            err_msg (str): error message.
            command_name (str): Command name.

        Returns:
            Tuple(List, List): tuple containing a
            list of return codes and a listof string msg.
            For Example: (ResultCode.OK, "").

        """
        return_codes = []  # ["ResultCode.OK","ResultCode.REJECTED"]
        message_or_unique_ids = []  # ["1234_AssignResources","InvalidJson"]

        for adapter in adapters:
            try:
                (
                    return_code,
                    message,
                ) = self.invoke_command_and_add_tracking_data(
                    adapter=adapter,
                    command_name=command_name,
                    command_input=argin,
                    callback=callback,
                )
                return_codes.append(return_code)
                message_or_unique_ids.append(message)
                self.logger.debug(
                    "Command invoked | command=%s device=%s",
                    command_name,
                    adapter.dev_name,
                )

            except Exception as e:
                return_codes.append(ResultCode.FAILED)
                message_or_unique_ids.append(
                    f"{err_msg} {adapter.dev_name}: {e}"
                )
                self.logger.error(
                    "Error in invoking %s on %s, Exception: %s",
                    command_name,
                    adapter.dev_name,
                    str(e),
                )
        self.logger.debug(
            "Command responses received | command=%s responses=%s",
            command_name,
            str(message_or_unique_ids),
        )
        return return_codes, message_or_unique_ids

    def invoke_commands_without_lrc(
        self,
        adapters: List,
        command_caller,
        err_msg: str,
        command_name: str,
    ) -> Tuple[List[ResultCode | Any], List[str | Any]]:
        """
        Invokes command on adapters

        Args:
            adapters: list of the adapters.
            command_caller: command caller.
            err_msg (str): error message.
            command_name (str): Command name.

        Returns:
            Tuple(List, List): tuple containing a
            list of return codes and a listof string msg.
            For Example: (ResultCode.OK, "").

        """
        return_codes = []  # ["ResultCode.OK","ResultCode.REJECTED"]
        message_or_unique_ids = []  # ["1234_AssignResources","InvalidJson"]

        for adapter in adapters:
            try:
                return_code, message_or_unique_id = command_caller(adapter)
                return_codes.append(return_code[0])
                message_or_unique_ids.append(message_or_unique_id[0])
                self.logger.debug(
                    "Command invoked | command=%s device=%s",
                    command_name,
                    adapter.dev_name,
                )

            except Exception as e:
                return_codes.append(ResultCode.FAILED)
                message_or_unique_ids.append(
                    f"{err_msg} {adapter.dev_name}: {e}"
                )
                self.logger.error(
                    "Error in invoking | command=%s device=%s error=%s",
                    command_name,
                    adapter.dev_name,
                    str(e),
                )
        self.logger.debug(
            "Current message_or_uniques_ids: %s", str(message_or_unique_ids)
        )
        return return_codes, message_or_unique_ids

    def send_command(
        self,
        adapters: Optional[AdapterFactory],
        description: str,
        command: str,
        argin=None,
    ) -> Tuple[List[ResultCode | Any], List[str | Any]]:
        """
        Submit command in progress

        Args:
            adapters: list of the adapters.
            description (str): message.
            command (str): Command name.
            argin: Command input argument.

        Returns:
            Tuple(List, List): Tuple of list of ResultCodes
            and messages

        """
        if argin is None:
            return self.invoke_commands_without_lrc(
                adapters, operator.methodcaller(command), description, command
            )
        return self.invoke_commands_without_lrc(
            adapters,
            operator.methodcaller(command, argin),
            description,
            command,
        )

    def reject_command(self, message: str) -> Tuple[TaskStatus, str]:
        """
        Rejects command method for logs error message.

        Args:
            message (str): Error message

        Returns:
            A tuple containing a return code and a string msg.
            For Example: (TaskStatus.REJECTED, "")

        """
        self.logger.error(
            "Command execution failed due to reason: %s", message
        )
        return TaskStatus.REJECTED, message

    def adapter_error_message(
        self, dev_name: str, error
    ) -> Tuple[ResultCode, str]:
        """
        Adapter Error message

        Args:
            dev_name (str): name of the device.
            error: error message.

        Returns:
            A tuple containing a return code and a string msg.
            For Example: (ResultCode.FAILED, "")

        """
        message = f"Adapter creation failed for {dev_name}: {str(error)}"
        self.logger.error(message)
        return ResultCode.FAILED, message

    def invoke_command_and_add_tracking_data(
        self, adapter, command_name, command_input=None, callback=None
    ):
        """Update command tracking data"""
        try:
            if not callback:
                callback = self.invoke_command_lrc_cb
            lrc_data = invoke_lrc(
                callback(adapter.dev_name),
                adapter._proxy,
                command_name,
                command_args=(command_input,) if command_input else None,
                logger=self.logger,
            )
            self.command_device_id_map[adapter.dev_name] = lrc_data.command_id
            self.command_subs_list.append(lrc_data)
        except CommandError as err:
            self.logger.error("command error %s", str(err))
            error_message = (
                f"Command Error for device {adapter.dev_name}: {str(err)}"
            )
            return ResultCode.REJECTED, error_message
        except ResultCodeError as err:
            self.logger.error("ResultCode error %s", str(err))
            error_message = (
                f"error occurred for device {adapter.dev_name}: {str(err)}"
            )
            return ResultCode.FAILED, error_message
        return ResultCode.OK, ""

    def wait_for_command_completion(
        self,
        device_length: int,
        desired_state=None,
        function_name=None,
        use_command_class_id=False,
    ):
        """This Method wait for desired obs state"""
        all_results_ok = False
        end_time = time.monotonic() + self.component_manager.command_timeout
        self.logger.debug(
            "Command subscription list %s", self.command_subs_list
        )
        with self.component_manager.command_completion_cond:
            while True:
                self.logger.debug(
                    "Command progress | received=%s/%s",
                    len(self.command_results.keys()),
                    self.command_results,
                )
                self.logger.debug("Device length: %s", device_length)
                if len(self.command_results.keys()) == device_length:
                    # All command results received check if any Failure
                    failed_results_info = {}
                    for device, result in self.command_results.items():
                        self.logger.info(result)
                        if result[0] != ResultCode.OK:
                            failed_results_info[device] = result

                    if failed_results_info:
                        exception_message = (
                            "Exception occurred on the following devices: "
                        )
                        for devname, error_value in sorted(
                            failed_results_info.items()
                        ):
                            _, error_message = error_value
                            exception_message += f"{devname}: {error_message}"

                        return ResultCode.FAILED, exception_message
                    all_results_ok = True
                self.logger.debug(
                    "function_name %s %s", function_name, all_results_ok
                )
                if (not function_name) and all_results_ok:
                    return ResultCode.OK, "Command Completed"
                if function_name:
                    if use_command_class_id:
                        state = getattr(self, function_name)()
                    else:
                        state = getattr(
                            self.component_manager, function_name
                        )()
                    if state == desired_state and all_results_ok:
                        return ResultCode.OK, "Command Completed"

                remaining = end_time - time.monotonic()
                if remaining <= 0:
                    if function_name and use_command_class_id:
                        data = getattr(self, function_name)()
                    elif function_name and not use_command_class_id:
                        data = getattr(self.component_manager, function_name)()
                    else:
                        data = None
                    self.logger.warning(
                        "No event command results | command=%s state=%s",
                        self.command_results,
                        data,
                    )
                    return (
                        ResultCode.FAILED,
                        "Timeout has occurred, command failed",
                    )

                self.component_manager.command_completion_cond.wait(remaining)

    def invoke_command_lrc_cb(self, device_name: str):
        """Invoke LRC callback.
        Provide this callback whenever command is invoked using invoke_lrc api
        Args:
            device_name: Name Of Device
        Returns:
            callback: function object to provided to invoke_lrc
        """

        def callback(result=None, **kwargs):
            LOGGER.debug(
                "Received command result %s from device %s",
                result,
                device_name,
            )
            if result:
                with self.component_manager.command_completion_cond:
                    self.command_results[device_name] = result
                    cond = self.component_manager.command_completion_cond
                    with cond:
                        cond.notify_all()

        return callback


class TelescopeOnOff(CentralNodeCommand):
    """Central node abstract command class"""

    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(component_manager, *args, logger=logger, **kwargs)
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.csp_mln_adapter = None
        self.sdp_mln_adapter = None
        self.subarray_adapters = []
        self.dish_adapters = []

    def init_adapters_mid(self) -> Tuple[ResultCode, str]:
        """
        Initialises adapters for mid

        Returns:
            Tuple(ResultCode, str): Tuple containing
            ResultCode and message

        """
        self.csp_mln_adapter = None
        self.sdp_mln_adapter = None
        self.subarray_adapters = []
        self.dish_adapters = []
        try:
            self.csp_mln_adapter = self._adapter_factory.get_or_create_adapter(
                self.component_manager.input_parameter.csp_mln_dev_name,
                AdapterType.CSP_MASTER_LEAF_NODE,
            )
            self.logger.debug(
                "Adapter created | type=CSP_MASTER_LEAF_NODE device=%s",
                self.component_manager.input_parameter.csp_mln_dev_name,
            )
        except Exception as e:
            return self.adapter_error_message(
                self.component_manager.input_parameter.csp_mln_dev_name,
                e,
            )

        try:
            self.sdp_mln_adapter = self._adapter_factory.get_or_create_adapter(
                self.component_manager.input_parameter.sdp_mln_dev_name
            )
            self.logger.debug(
                "Adapter is created for SDP Master Leaf Node: %s",
                self.component_manager.input_parameter.sdp_mln_dev_name,
            )
        except Exception as e:
            return self.adapter_error_message(
                self.component_manager.input_parameter.sdp_mln_dev_name,
                e,
            )

        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in self.component_manager.input_parameter.subarray_dev_names:
            devInfo = self.component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.subarray_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.SUBARRAY
                        )
                    )
                    num_working += 1
                    self.logger.debug(
                        "Adapter is created for SubarrayNode: %s", dev_name
                    )
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter | device=%s error=%s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            message = f"Error in creating tm subarray adapters {faulty_dev},"
            return (
                ResultCode.FAILED,
                message,
            )

        error_dev_names = []
        num_working = 0
        for (
            dev_name
        ) in self.component_manager.input_parameter.dish_leaf_node_dev_names:
            devInfo = self.component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    # import debugpy; debugpy.debug_this_thread()
                    self.dish_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                    self.logger.debug("Adapter is created for %s", dev_name)
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter for %s, Exception: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            message = (
                f"Error in creating dish adapters {'.'.join(error_dev_names)}"
            )
            return (ResultCode.FAILED, message)

        return ResultCode.OK, ""

    def init_adapters_low(self) -> Tuple[ResultCode, str]:
        """
        Initialises adapter low

        Returns:
            Tuple(ResultCode, str): Tuple containing
            ResultCode and message

        """
        self.csp_mln_adapter = None
        self.sdp_mln_adapter = None
        self.mccs_mln_adapter = None
        self.subarray_adapters = []

        try:
            self.csp_mln_adapter = self._adapter_factory.get_or_create_adapter(
                self.component_manager.input_parameter.csp_mln_dev_name
            )
            self.logger.debug(
                "Adapter is created for CSP Master Leaf Node: %s",
                self.component_manager.input_parameter.csp_mln_dev_name,
            )
        except Exception as e:
            return self.adapter_error_message(
                self.component_manager.input_parameter.csp_mln_dev_name,
                e,
            )

        try:
            self.mccs_mln_adapter = (
                self._adapter_factory.get_or_create_adapter(
                    self.component_manager.input_parameter.mccs_mln_dev_name,
                    AdapterType.MCCS_MASTER_LEAF_NODE,
                )
            )
            self.logger.debug(
                "Adapter is created for MCCS Master Leaf Node: %s",
                self.component_manager.input_parameter.mccs_mln_dev_name,
            )

        except Exception as e:
            return (
                self.component_manager.input_parameter.mccs_mln_dev_name,
                e,
            )

        try:
            self.sdp_mln_adapter = self._adapter_factory.get_or_create_adapter(
                self.component_manager.input_parameter.sdp_mln_dev_name
            )
            self.logger.debug(
                "Adapter is created for SDP Master Leaf Node: %s",
                self.component_manager.input_parameter.sdp_mln_dev_name,
            )
        except Exception as e:
            return self.adapter_error_message(
                self.component_manager.input_parameter.sdp_mln_dev_name,
                e,
            )

        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in self.component_manager.input_parameter.subarray_dev_names:
            devInfo = self.component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.subarray_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.SUBARRAY
                        )
                    )
                    num_working += 1
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter for %s , Exception: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            message = f"Error in creating tm subarray adapters {faulty_dev},"
            return (
                ResultCode.FAILED,
                message,
            )

        return ResultCode.OK, ""


class AssignReleaseResources(CentralNodeCommand):
    """AssignResources command class"""

    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(component_manager, logger=logger, *args, **kwargs)
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.dish_adapters = []
        self.subarray_adapters = []

    def set_command_id(self, command_name: str) -> None:
        """
        Sets the command id for error propagation.

        :param command_name: name of the command.
        :type command_name: str
        """
        self.command_id = f"{time.time()}-{command_name}"
        self.logger.info(
            "Setting command id as %s for command: %s",
            self.command_id,
            command_name,
        )

    def init_adapters_mid(self) -> Tuple[ResultCode, str]:
        """
        Initialises adapters for mid

        Returns:
            Tuple(ResultCode, str):
            tuple of ResultCode and message.

        """
        self.dish_adapters = []
        self.subarray_adapters = []
        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in self.component_manager.input_parameter.subarray_dev_names:
            devInfo = self.component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.subarray_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.SUBARRAY
                        )
                    )
                    num_working += 1
                    self.logger.debug(
                        "Adapter is created for SubarrayNode: %s ", dev_name
                    )
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter for %s, Exception: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            message = f"Error in creating tm subarray adapters {faulty_dev},"
            return (
                ResultCode.FAILED,
                message,
            )

        error_dev_names = []
        num_working = 0
        for (
            dev_name
        ) in self.component_manager.input_parameter.dish_leaf_node_dev_names:
            devInfo = self.component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.dish_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                    self.logger.debug(
                        "Adapter is created for DishLeafNode: %s", dev_name
                    )
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter for %s, Exception: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return (
                ResultCode.FAILED,
                f"Error in creating dish adapters {'.'.join(error_dev_names)}",
            )

        return (ResultCode.OK, "")

    def init_adapters_low(self) -> Tuple[ResultCode, str]:
        """
        Initialises adapter for central node low

        Returns:
            Tuple(ResultCode, str):
            tuple of ResultCode and message.

        """
        self.mccs_mln_adapter = None
        self.subarray_adapters = []

        try:
            self.mccs_mln_adapter = (
                self._adapter_factory.get_or_create_adapter(
                    self.component_manager.input_parameter.mccs_mln_dev_name,
                    AdapterType.MCCS_MASTER_LEAF_NODE,
                )
            )
        except Exception as e:
            return (
                self.component_manager.input_parameter.mccs_mln_dev_name,
                e,
            )

        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in self.component_manager.input_parameter.subarray_dev_names:
            devInfo = self.component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.subarray_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.SUBARRAY
                        )
                    )
                    num_working += 1
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter for %s, Exception: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            message = f"Error in creating tm subarray adapters {faulty_dev},"
            return (ResultCode.FAILED, message)

        return (ResultCode.OK, "")

    def put_result_in_command_mapping_dict(
        self, return_codes, message_or_unique_ids
    ):
        """Update command_mapping dictionary to add the ResultCode and
        unique_id for the command executed"""

        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return (
                    ResultCode.FAILED,
                    message_or_unique_id,
                )

            # even if command is rejected by subarraynode ,
            # it will be resultcode failed for centralnode
            if return_code in [ResultCode.QUEUED, ResultCode.OK]:
                if self.component_manager.command_mapping.get(self.command_id):
                    self.logger.debug(
                        "Command ID: %s |"
                        + " Adding the ID %s to the command mapping"
                        + " dictionary under command_id: %s",
                        self.command_id,
                        message_or_unique_id,
                        self.command_id,
                    )
                    self.component_manager.command_mapping[
                        self.command_id
                    ].append(message_or_unique_id)
                else:
                    self.logger.debug(
                        "Command ID: %s |"
                        + " Creating a command mapping dictionary for id: "
                        + "%s, with unique_id: %s",
                        self.command_id,
                        self.command_id,
                        message_or_unique_id,
                    )
                    self.component_manager.command_mapping[self.command_id] = [
                        message_or_unique_id
                    ]
        return (ResultCode.OK, "")


class LoadDishCfgCommand(CentralNodeCommand):
    """This command class for LoadDishConfig command which
    load dishid-vcc map json from CAR and pass it to CSP Master
    """

    def __init__(
        self,
        component_manager,
        adapter_factory: Optional[AdapterFactory] = None,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(component_manager, *args, logger=logger, **kwargs)
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.csp_mln_adapter = None
        self.sdp_mln_adapter = None
        self.subarray_adapters = []
        self.dish_adapters = []

    def init_adapters_mid(self) -> Tuple[ResultCode, str]:
        """Initialises Adapters for mid"""
        self.csp_mln_adapter: Optional[AdapterFactory] = None
        self.sdp_mln_adapter: Optional[AdapterFactory] = None
        self.subarray_adapters: Optional[AdapterFactory] = []
        self.dish_adapters = []
        try:
            self.csp_mln_adapter = self._adapter_factory.get_or_create_adapter(
                self.component_manager.input_parameter.csp_mln_dev_name,
                AdapterType.CSP_MASTER_LEAF_NODE,
            )
            self.logger.debug(
                "Adapter is created for CSP Master Leaf Node: %s",
                self.component_manager.input_parameter.csp_mln_dev_name,
            )
        except Exception as e:
            return self.adapter_error_message(
                self.component_manager.input_parameter.csp_mln_dev_name,
                e,
            )
        error_dev_names = []
        num_working = 0
        for (
            dev_name
        ) in self.component_manager.input_parameter.dish_leaf_node_dev_names:
            devInfo = self.component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.dish_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                    self.logger.debug(
                        "Adapter is created for DishLeafNode: %s", dev_name
                    )
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter for %s, Exception: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return (
                ResultCode.FAILED,
                f"Error in creating dish adapters {'.'.join(error_dev_names)}",
            )
        return (ResultCode.OK, "")


class SetDishGPM(CentralNodeCommand):
    """This command class for SetGlobalPointingModel command which
    forms GPM json CAR URI and pass it to TMC Dish Leaf Node.
    """

    def __init__(
        self,
        component_manager,
        adapter_factory: Optional[AdapterFactory] = None,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(component_manager, *args, logger=logger, **kwargs)
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.csp_mln_adapter = None
        self.sdp_mln_adapter = None
        self.subarray_adapters = []
        self.dish_adapters = []

    def init_adapters_mid(self) -> Tuple[ResultCode, str]:
        """Initialises Adapters for mid"""
        self.csp_mln_adapter: Optional[AdapterFactory] = None
        self.sdp_mln_adapter: Optional[AdapterFactory] = None
        self.subarray_adapters: Optional[AdapterFactory] = []
        self.dish_adapters = []
        error_dev_names = []
        num_working = 0
        for (
            dev_name
        ) in self.component_manager.input_parameter.dish_leaf_node_dev_names:
            devInfo = self.component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.dish_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                    self.logger.debug(
                        "Adapter is created for DishLeafNode: %s", dev_name
                    )
                except Exception as e:
                    self.logger.exception(
                        "Exception in creating adapter for %s, Exception: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return (
                ResultCode.FAILED,
                f"Error in creating dish adapters {'.'.join(error_dev_names)}",
            )
        return (ResultCode.OK, "")

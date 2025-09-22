"""Command class for central node"""

# pylint:disable =abstract-method
import logging
import operator
import time
from typing import Any, List, Optional, Tuple, Union

from ska_ser_logging import configure_logging
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
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
                self.logger.info(
                    "%s invoked on %s ", command_name, adapter.dev_name
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
        self.logger.info(
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
            return self.invoke_command(
                adapters, operator.methodcaller(command), description, command
            )
        return self.invoke_command(
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
                "Adapter is created for CSP Master Leaf Node: %s",
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

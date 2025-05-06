"""Abstract Command class for central node"""
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
    """Central node abstract command class"""

    def __init__(
        self,
        component_manager,
        *args,
        logger: logging.Logger = LOGGER,
        **kwargs,
    ):
        super().__init__(component_manager, *args, logger=logger, **kwargs)
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
        """Invokes command on adapter"""
        return_codes = []  # ["ResultCode.OK","ResultCode.REJECTED"]
        message_or_unique_ids = []  # ["1234_AssignResources","InvalidJson"]

        for adapter in adapters:
            try:
                return_code, message_or_unique_id = command_caller(adapter)
                return_codes.append(return_code[0])
                message_or_unique_ids.append(message_or_unique_id[0])
                self.logger.info(
                    f"Invoked {command_name} on  {adapter.dev_name}"
                )

            except Exception as e:
                return_codes.append(ResultCode.FAILED)
                message_or_unique_ids.append(
                    f"{err_msg} {adapter.dev_name}: {e}"
                )
                self.logger.error(
                    "Error in invoking %s on %s: %s",
                    command_name,
                    adapter.dev_name,
                    str(e),
                )
        self.logger.info(
            "Current message_or_uniques_ids" + str(message_or_unique_ids)
        )
        return return_codes, message_or_unique_ids

    def send_command(
        self,
        adapters: Optional[AdapterFactory],
        description: str,
        command: str,
        argin=None,
    ):
        """Submit command in progress"""
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

    def reject_command(self, message: str) -> Tuple[ResultCode, str]:
        """Rejects command method for logs error message."""
        self.logger.error(
            "Command execution failed due to reason : %s", message
        )
        return TaskStatus.REJECTED, message

    def adapter_error_message(
        self, dev_name: str, error
    ) -> Tuple[ResultCode, str]:
        """Adapter Error message"""
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
        """Initialises adapters for mid"""
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
                "Adapter is created for CSP Master Leaf Node %s",
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
                "Adapter is created for SDP Master Leaf Node %s",
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
                        f"Adapter is created for SubarrayNode {dev_name}",
                    )
                except Exception as e:
                    self.logger.error(
                        "Error in creating adapter for %s: %s",
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
                    self.logger.debug(
                        "Adapter is created for DishLeafNode %s", dev_name
                    )
                except Exception as e:
                    self.logger.error(
                        "Error in creating adapter for %s: %s",
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
        """Initialises adapter low"""
        self.csp_mln_adapter = None
        self.sdp_mln_adapter = None
        self.mccs_mln_adapter = None
        self.subarray_adapters = []

        try:
            self.csp_mln_adapter = self._adapter_factory.get_or_create_adapter(
                self.component_manager.input_parameter.csp_mln_dev_name
            )
            self.logger.debug(
                "Adapter is created for CSP Master Leaf Node %s",
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
                "Adapter is created for MCCS Master Leaf Node %s",
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
                "Adapter is created for SDP Master Leaf Node %s",
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
                    self.logger.error(
                        "Error in creating adapter for %s: %s",
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
        """Initialises adapter for mid"""
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
                        f"Adapter is created for SubarrayNode {dev_name}"
                    )
                except Exception as e:
                    self.logger.error(
                        "Error in creating adapter for %s: %s",
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
                        f"Adapter is created for DishLeafNode {dev_name}"
                    )
                except Exception as e:
                    self.logger.error(
                        "Error in creating adapter for %s: %s",
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
        """Initialises adapter for central node low"""
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
                    self.logger.error(
                        "Error in creating adapter for %s: %s",
                        dev_name,
                        str(e),
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            faulty_dev = ".".join(error_dev_names)
            message = f"Error in creating tm subarray adapters {faulty_dev},"
            return (ResultCode.FAILED, message)

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
                "Adapter is created for CSP Master Leaf Node %s",
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
                        f"Adapter is created for DishLeafNode {dev_name}"
                    )
                except Exception as e:
                    self.logger.error(
                        "Error in creating adapter for %s: %s",
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

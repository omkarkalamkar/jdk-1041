import operator
import time
from typing import Callable, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import TimeoutCallback
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.tmc_command import TMCCommand

from ska_tmc_centralnode.model.input import InputParameterMid


class CentralNodeCommand(TMCCommand):
    def __init__(self, component_manager, *args, logger=None, **kwargs):
        super().__init__(component_manager, *args, logger=logger, **kwargs)
        self.command_id = f"{time.time()}_{self.__class__.__name__}"
        self.timeout_id = f"{time.time()}_{self.__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)
        self.task_callback: Callable | None = None

    def init_adapters(self) -> Tuple[ResultCode, str]:
        if isinstance(
            self.component_manager.input_parameter, InputParameterMid
        ):
            result, message = self.init_adapters_mid()
        else:
            result, message = self.init_adapters_low()

        return result, message

    def do(self, argin=None):
        if isinstance(
            self.component_manager.input_parameter, InputParameterMid
        ):
            result = self.do_mid(argin)
        else:
            result = self.do_low(argin)

        return result

    def invoke_command(
        self,
        adapters: list,
        command_caller,
        err_msg: str,
        command_name: str,
    ):
        return_codes = []  # ["ResultCode.OK","ResultCode.REJECTED"]
        message_or_unique_ids = []  # ["1234_AssignResources","InvalidJson"]
        try:
            for adapter in adapters:
                return_code, message_or_unique_id = command_caller(adapter)
                return_codes.append(return_code[0])
                message_or_unique_ids.append(message_or_unique_id[0])
                self.logger.debug(
                    f"Invoked {command_name} on device {adapter.dev_name}"
                )

        except Exception as e:
            return (
                [ResultCode.FAILED],
                [f"{err_msg} {adapter.dev_name}: {e}"],
            )
        return return_codes, message_or_unique_ids

    def send_command(self, adapters, description, command, argin=None):
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

    def reject_command(self, message):
        self.logger.error(message)
        return TaskStatus.REJECTED, message

    def adapter_error_message(
        self, dev_name: str, error
    ) -> Tuple[ResultCode, str]:
        message = f"Adapter creation failed for {dev_name}: {str(error)}"
        self.logger.error(message)
        return ResultCode.FAILED, message


class AbstractTelescopeOnOff(CentralNodeCommand):
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
        self.csp_mln_adapter = None
        self.sdp_mln_adapter = None
        self.subarray_adapters = []
        self.dish_adapters = []
        try:
            self.csp_mln_adapter = self._adapter_factory.get_or_create_adapter(
                self.component_manager.input_parameter.csp_mln_dev_name
            )
            self.logger.debug(
                f"Adapter is created for CSP Master Leaf Node {self.component_manager.input_parameter.csp_mln_dev_name}: {self.csp_mln_adapter}"
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
                f"Adapter is created for SDP Master Leaf Node {self.component_manager.input_parameter.sdp_mln_dev_name}: {self.sdp_mln_adapter}"
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
                        f"Adapter is created for SubarrayNode {dev_name}"
                    )
                except Exception as e:
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            message = f"Error in creating tm subarray adapters {'.'.join(error_dev_names)}"
            return (ResultCode.FAILED, message)

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
                        f"Adapter is created for DishLeafNode {dev_name}"
                    )
                except Exception as e:
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            message = (
                f"Error in creating dish adapters {'.'.join(error_dev_names)}"
            )
            return (ResultCode.FAILED, message)

        return ResultCode.OK, ""

    def init_adapters_low(self) -> Tuple[ResultCode, str]:
        self.csp_mln_adapter = None
        self.sdp_mln_adapter = None
        self.mccs_mln_adapter = None
        self.subarray_adapters = []

        try:
            self.csp_mln_adapter = self._adapter_factory.get_or_create_adapter(
                self.component_manager.input_parameter.csp_mln_dev_name
            )
            self.logger.debug(
                f"Adapter is created for CSP Master Leaf Node {self.component_manager.input_parameter.csp_mln_dev_name}: {self.csp_mln_adapter}"
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
                f"Adapter is created for MCCS Master Leaf Node {self.component_manager.input_parameter.mccs_mln_dev_name}: {self.mccs_mln_adapter}"
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
                f"Adapter is created for SDP Master Leaf Node {self.component_manager.input_parameter.sdp_mln_dev_name}: {self.sdp_mln_adapter}"
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
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            message = f"Error in creating tm subarray low adapters {'.'.join(error_dev_names)}"
            return (ResultCode.FAILED, message)

        return ResultCode.OK, ""


class AbstractAssignReleaseResources(CentralNodeCommand):
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
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return (
                ResultCode.FAILED,
                f"Error in creating tm subarray adapters {'.'.join(error_dev_names)}",
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
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return (
                ResultCode.FAILED,
                f"Error in creating dish adapters {'.'.join(error_dev_names)}",
            )

        return (ResultCode.OK, "")

    def init_adapters_low(self) -> Tuple[ResultCode, str]:
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
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return (
                ResultCode.FAILED,
                f"Error in creating tm subarray adapters {'.'.join(error_dev_names)}",
            )

        return (ResultCode.OK, "")

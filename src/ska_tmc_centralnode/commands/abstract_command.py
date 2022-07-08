import operator

from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.tmc_command import TMCCommand
from tango import DevState

from ska_tmc_centralnode.model.input import InputParameterMid


class CentralNodeCommand(TMCCommand):
    def __init__(self, component_manager, *args, logger=None, **kwargs):
        super().__init__(component_manager, *args, logger=logger, **kwargs)

    def check_allowed(self):
        component_manager = self.component_manager

        if isinstance(component_manager.input_parameter, InputParameterMid):
            result = self.check_allowed_mid()
        else:
            result = self.check_allowed_low()

        return result

    def init_adapters(self):
        component_manager = self.component_manager

        if isinstance(component_manager.input_parameter, InputParameterMid):
            result, message = self.init_adapters_mid()
        else:
            result, message = self.init_adapters_low()

        return result, message

    def do(self, argin=None):
        component_manager = self.component_manager

        if isinstance(component_manager.input_parameter, InputParameterMid):
            result = self.do_mid(argin)
        else:
            result = self.do_low(argin)

        return result

    def invoke_command(
        self,
        adapters: list,
        command_caller,
        err_msg: str,
    ):
        try:
            for adapter in adapters:
                command_caller(adapter)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                f"{err_msg} {adapter.dev_name}: {e}",
            )
        return (ResultCode.OK, "")

    def send_command(self, adapters, description, command, argin=None):
        if argin:
            return self.invoke_command(
                adapters, operator.methodcaller(command, argin), description
            )
        return self.invoke_command(
            adapters, operator.methodcaller(command), description
        )


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
        self.tm_leaf_csp_master_adapter = None
        self.tm_leaf_sdp_master_adapter = None
        self.tm_subarray_adapters = []
        self.tm_dish_adapters = []

    def check_allowed_mid(self):
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the
        component needed for the operation are not unresponsive

        :return: True if this command is allowed

        :rtype: boolean

        """
        component_manager = self.component_manager
        component_manager.check_if_command_is_allowed()

        # for this command I need a number of sub-devices
        # import debugpy; debugpy.debug_this_thread()
        component_manager.check_if_csp_mln_is_responsive()
        component_manager.check_if_sdp_mln_is_responsive()
        component_manager.check_if_subarrays_are_responsive()
        component_manager.check_if_dishes_are_responsive()

        return True

    def check_allowed_low(self):
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the
        component needed for the operation are not unresponsive

        :return: True if this command is allowed

        :rtype: boolean

        """
        component_manager = self.component_manager

        component_manager.check_if_mccs_mln_is_responsive()
        component_manager.check_if_subarrays_are_responsive()

        return True

    def init_adapters_mid(self):
        self.tm_leaf_csp_master_adapter = None
        self.tm_leaf_sdp_master_adapter = None
        self.tm_subarray_adapters = []
        self.tm_dish_adapters = []
        component_manager = self.component_manager

        try:
            self.tm_leaf_csp_master_adapter = self._adapter_factory.get_or_create_adapter(
                component_manager.input_parameter.tm_leaf_csp_master_dev_name
            )
        except Exception as e:
            return self.adapter_error_message_result(
                component_manager.input_parameter.tm_leaf_csp_master_dev_name,
                e,
            )

        try:
            self.tm_leaf_sdp_master_adapter = self._adapter_factory.get_or_create_adapter(
                component_manager.input_parameter.tm_leaf_sdp_master_dev_name
            )
        except Exception as e:
            return self.adapter_error_message_result(
                component_manager.input_parameter.tm_leaf_sdp_master_dev_name,
                e,
            )

        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.tm_subarray_adapters.append(
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
            message = f"Error in creating tm subarray adapters {'.'.join(error_dev_names)}"
            return self.generate_command_result(ResultCode.FAILED, message)

        error_dev_names = []
        num_working = 0
        for dev_name in component_manager.input_parameter.tm_dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    # import debugpy; debugpy.debug_this_thread()
                    self.tm_dish_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                except Exception as e:
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            message = (
                f"Error in creating dish adapters {'.'.join(error_dev_names)}"
            )
            return self.generate_command_result(ResultCode.FAILED, message)

        return ResultCode.OK, ""

    def init_adapters_low(self):
        self.tm_leaf_mccs_master_adapter = None
        self.tm_subarray_adapters = []
        component_manager = self.component_manager

        try:
            self.tm_leaf_mccs_master_adapter = (
                self._adapter_factory.get_or_create_adapter(
                    component_manager.input_parameter.mccs_master_leaf_node,
                    AdapterType.MCCS,
                )
            )
        except Exception as e:
            return self.adapter_error_message_result(
                component_manager.input_parameter.mccs_master_leaf_node,
                e,
            )

        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.tm_subarray_adapters.append(
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
            return self.generate_command_result(ResultCode.FAILED, message)

        return ResultCode.OK, ""


class AbstractAssignReleaseResources(CentralNodeCommand):
    def __init__(
        self,
        target,
        pop_state_model,
        adapter_factory=None,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(target, args, logger, kwargs)
        self.op_state_model = pop_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.tm_dish_adapters = []
        self.tm_subarray_adapters = []

    def check_allowed_mid(self):
        """
        Checks whether this command is allowed to be run in current device state

        :return: True if this command is allowed to be run in current device state

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state

        """
        component_manager = self.target

        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                "AssignReleaseResources() is not allowed in current state %s",
                self.op_state_model.op_state,
            )
        component_manager.check_if_subarrays_are_responsive()
        component_manager.check_if_dishes_are_responsive()

        return True

    def check_allowed_low(self):
        """
        Checks whether this command is allowed to be run in current device state

        :return: True if this command is allowed to be run in current device state

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state

        """
        component_manager = self.target

        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                "AssignReleaseResources() is not allowed in current state %s",
                self.op_state_model.op_state,
            )

        component_manager.check_if_mccs_mln_is_responsive()
        component_manager.check_if_subarrays_are_responsive()

        return True

    def init_adapters_mid(self):

        self.tm_dish_adapters = []
        self.tm_subarray_adapters = []
        component_manager = self.target

        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.tm_subarray_adapters.append(
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
            return self.generate_command_result(
                ResultCode.FAILED,
                f"Error in creating tm subarray adapters {'.'.join(error_dev_names)}",
            )

        error_dev_names = []
        num_working = 0
        for dev_name in component_manager.input_parameter.tm_dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.tm_dish_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                except Exception as e:
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return self.generate_command_result(
                ResultCode.FAILED,
                f"Error in creating dish adapters {'.'.join(error_dev_names)}",
            )

        return (ResultCode.OK, "")

    def init_adapters_low(self):

        self.tm_leaf_mccs_master_adapter = None
        self.tm_subarray_adapters = []
        component_manager = self.target

        try:
            self.tm_leaf_mccs_master_adapter = (
                self._adapter_factory.get_or_create_adapter(
                    component_manager.input_parameter.mccs_master_leaf_node,
                    AdapterType.MCCS,
                )
            )
        except Exception as e:
            return self.adapter_error_message_result(
                component_manager.input_parameter.mccs_master_leaf_node,
                e,
            )

        error_dev_names = []
        num_working = 0

        for (
            dev_name
        ) in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.tm_subarray_adapters.append(
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
            return self.generate_command_result(
                ResultCode.FAILED,
                f"Error in creating tm subarray adapters {'.'.join(error_dev_names)}",
            )

        return (ResultCode.OK, "")

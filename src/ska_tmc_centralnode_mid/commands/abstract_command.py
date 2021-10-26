from ska_tango_base.commands import BaseCommand, ResultCode
from tango import DevState

from ska_tmc_centralnode_mid.exceptions import CommandNotAllowed
from ska_tmc_centralnode_mid.manager.adapters import (
    AdapterFactory,
    AdapterType,
)
from ska_tmc_centralnode_mid.model.input import InputParameterMid


class TMCCommand(BaseCommand):
    def __init__(self, target, *args, logger=None, **kwargs):
        super().__init__(target, args, logger, kwargs)

    def generate_command_result(self, result_code, message):
        if result_code == ResultCode.FAILED:
            self.logger.error(message)
        self.logger.info(message)
        return (result_code, message)

    def adapter_error_message_result(self, dev_name, e):
        message = f"Error in creating adapter for {dev_name}: {e}"
        self.logger.error(message)
        return ResultCode.FAILED, message

    def check_allowed(self):
        component_manager = self.target

        if isinstance(component_manager.input_parameter, InputParameterMid):
            result = self.check_allowed_mid()
        else:
            result = self.check_allowed_low()

        return result

    def init_adapters(self):
        component_manager = self.target

        if isinstance(component_manager.input_parameter, InputParameterMid):
            result, message = self.init_adapters_mid()
        else:
            result, message = self.init_adapters_low()

        return result, message

    def do(self, argin=None):
        component_manager = self.target

        if isinstance(component_manager.input_parameter, InputParameterMid):
            result = self.do_mid(argin)
        else:
            result = self.do_low(argin)

        return result

    def check_allowed_mid(self):
        raise NotImplementedError("This class must be inherited!")

    def check_allowed_low(self):
        raise NotImplementedError("This class must be inherited!")

    def init_adapters_mid(self):
        raise NotImplementedError("This class must be inherited!")

    def init_adapters_low(self):
        raise NotImplementedError("This class must be inherited!")

    def do_mid(self, argin=None):
        raise NotImplementedError("This class must be inherited!")

    def do_low(self, argin=None):
        raise NotImplementedError("This class must be inherited!")


class AbstractTelescopeOnOff(TMCCommand):
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
        component_manager = self.target

        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                "TelescopeOnOff() is not allowed in current state %s",
                self.op_state_model.op_state,
            )

        # for this command I need a number of sub-devices
        # import debugpy; debugpy.debug_this_thread()
        devInfo = component_manager.get_device(
            component_manager.input_parameter.tm_leaf_csp_master_dev_name
        )
        if devInfo is None or devInfo.unresponsive:
            raise CommandNotAllowed("TM Csp Master Leaf node not available")

        devInfo = component_manager.get_device(
            component_manager.input_parameter.tm_leaf_sdp_master_dev_name
        )
        if devInfo is None or devInfo.unresponsive:
            raise CommandNotAllowed("TM SDP Master Leaf node not available")

        subarray_count = 0
        for (
            dev_name
        ) in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.unresponsive:
                subarray_count += 1
        if subarray_count == 0:
            raise CommandNotAllowed("No TM Subarray available")

        dish_count = 0
        for dev_name in component_manager.input_parameter.tm_dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.unresponsive:
                dish_count += 1
        if dish_count == 0:
            raise CommandNotAllowed("No Dish available")

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
        component_manager = self.target

        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                "TelescopeOnOff() is not allowed in current state %s",
                self.op_state_model.op_state,
            )

        # for this command I need a number of sub-devices
        # import debugpy; debugpy.debug_this_thread()
        devInfo = component_manager.get_device(
            component_manager.input_parameter.mccs_master_leaf_node
        )
        if devInfo is None or devInfo.unresponsive:
            raise CommandNotAllowed("TM Mccs Master Leaf node not available")

        subarray_count = 0
        for (
            dev_name
        ) in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.unresponsive:
                subarray_count += 1
        if subarray_count == 0:
            raise CommandNotAllowed("No TM Low Subarray available")

        return True

    def init_adapters_mid(self):

        self.tm_leaf_csp_master_adapter = None
        self.tm_leaf_sdp_master_adapter = None
        self.tm_subarray_adapters = []
        self.tm_dish_adapters = []
        component_manager = self.target

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
        component_manager = self.target

        try:
            self.tm_leaf_mccs_master_adapter = (
                self._adapter_factory.get_or_create_adapter(
                    component_manager.input_parameter.mccs_master_leaf_node
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


class AbstractAssignReleaseResources(TMCCommand):
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

        subarray_count = 0
        for (
            dev_name
        ) in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.unresponsive:
                subarray_count += 1
        if subarray_count == 0:
            raise CommandNotAllowed("No TM Low Subarray available")

        dish_count = 0
        for dev_name in component_manager.input_parameter.tm_dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.unresponsive:
                dish_count += 1
        if dish_count == 0:
            raise CommandNotAllowed("No Dish available")

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
        
        devInfo = component_manager.get_device(
            component_manager.input_parameter.mccs_master_leaf_node
        )
        if devInfo is None or devInfo.unresponsive:
            raise CommandNotAllowed("TM Mccs Master Leaf node not available")

        subarray_count = 0
        for (
            dev_name
        ) in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.unresponsive:
                subarray_count += 1
        if subarray_count == 0:
            raise CommandNotAllowed("No TM Low Subarray available")

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
                    component_manager.input_parameter.mccs_master_leaf_node
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

from tango import DevState

from ska_tango_base.commands import BaseCommand
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.manager.adapters import AdapterType, AdapterFactory


class TMCCommand(BaseCommand):

    def __init__(self, target, *args, logger=None, **kwargs):
        super().__init__(target, args, logger, kwargs)

    def generate_command_result(self, cmd_name, result_code, message):
        if result_code == ResultCode.FAILED:
            self.logger.error(message)
        self.logger.info(message)
        self.target.add_command_execution(cmd_name, result_code, message)
        return (result_code, message)
    
    def adapter_error_message_result(self, dev_name, e):
        component_manager = self.target
        result_code = ResultCode.FAILED
        message = f"Error in creating adapter for {dev_name}: {e}"
        self.logger.error(message)
        component_manager.add_command_execution("AbstractTelescopeOnOff", result_code, message)
        return result_code,message


class AbstractTelescopeOnOff(TMCCommand):

    def __init__(self, target, pop_state_model, adapter_factory = AdapterFactory(), *args, logger=None, **kwargs):
        super().__init__(target, args, logger, kwargs)
        self.op_state_model = pop_state_model
        self._adapter_factory = adapter_factory
        self.tm_leaf_csp_master_adapter = None
        self.tm_leaf_sdp_master_adapter = None
        self.tm_subarray_adapters = []
        self.tm_dish_adapters = []

    def check_allowed(self):
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the 
        component needed for the operation are not faulty

        :return: True if this command is allowed

        :rtype: boolean

        """
        component_manager = self.target

        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            self.logger.error("TelescopeOnOff() is not allowed in current state %s", self.op_state_model.op_state)
            return False

        # for this command I need a number of sub-devices
        devInfo = component_manager.get_device(component_manager.input_parameter.tm_leaf_csp_master_dev_name)
        if devInfo is None or devInfo.faulty:
            self.logger.info("TM Csp Master Leaf node not available")
            return False
        
        devInfo = component_manager.get_device(component_manager.input_parameter.tm_leaf_sdp_master_dev_name)
        if devInfo is None or devInfo.faulty:
            self.logger.info("TM SDP Master Leaf node not available")
            return False
        
        subarray_count = 0
        for dev_name in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.faulty:
                subarray_count += 1
        if subarray_count == 0: 
            self.logger.info("No TM Subarray available")
            return False

        dish_count = 0
        for dev_name in component_manager.input_parameter.tm_dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.faulty:
                dish_count += 1
        if dish_count == 0: 
            self.logger.info("No Dish available")
            return False

        return True

    def init_adapters(self, cmd_name, component_manager):
        
        self.tm_leaf_csp_master_adapter = None
        self.tm_leaf_sdp_master_adapter = None
        self.tm_subarray_adapters = []
        self.tm_dish_adapters = []
        
        try:
            self.tm_leaf_csp_master_adapter = self._adapter_factory.get_or_create_adapter(
                component_manager.input_parameter.tm_leaf_csp_master_dev_name)
        except Exception as e:
            return self.adapter_error_message_result(component_manager.input_parameter.tm_leaf_csp_master_dev_name, e)
        
        try:
            self.tm_leaf_sdp_master_adapter = self._adapter_factory.get_or_create_adapter(
                component_manager.input_parameter.tm_leaf_sdp_master_dev_name)
        except Exception as e:
            return self.adapter_error_message_result(component_manager.input_parameter.tm_leaf_sdp_master_dev_name, e)

        error_dev_names = []
        num_working = 0

        for dev_name in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.faulty:
                try:
                    self.tm_subarray_adapters.append(self._adapter_factory.get_or_create_adapter(dev_name))
                    num_working += 1
                except Exception as e:
                    self.logger.warning("Error in creating adapter for %s: %s", dev_name, e)
                    error_dev_names.append(dev_name)
        
        if num_working == 0:
            message = f"Error in creating tm subarray adapters {'.'.join(error_dev_names)}"
            self.logger.error(message)
            component_manager.add_command_execution(cmd_name, ResultCode.FAILED, message)
            return ResultCode.FAILED, message

        error_dev_names = []
        num_working = 0
        for dev_name in component_manager.input_parameter.tm_dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.faulty:
                try:
                    self.tm_dish_adapters.append(self._adapter_factory.get_or_create_adapter(dev_name, AdapterType.DISH))
                    num_working += 1
                except Exception as e:
                    self.logger.warning("Error in creating adapter for %s: %s", dev_name, e)
                    error_dev_names.append(dev_name)
        
        if num_working == 0:
            message = f"Error in creating dish adapters {'.'.join(error_dev_names)}"
            self.logger.error(message)
            component_manager.add_command_execution(cmd_name, ResultCode.FAILED, message)
            return ResultCode.FAILED, message
        
        return ResultCode.OK, ""

    def do(self):
        raise NotImplementedError("This class must be inherited!")

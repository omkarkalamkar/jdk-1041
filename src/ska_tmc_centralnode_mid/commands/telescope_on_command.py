from tango import DevState

from ska_tango_base.commands import BaseCommand
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.manager.adapters import AdapterType, AdapterFactory

class AbstractTelescopeOnOff(BaseCommand):

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
        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            self.logger.error("TelescopeOnOff() is not allowed in current state %s", self.op_state_model.op_state)
            return False

        # for this command I need a number of sub-devices
        component_manager = self.target
        
        devInfo = component_manager.get_device(component_manager.input_parameter.tm_leaf_csp_master_dev_name)
        if devInfo.faulty:
            self.logger.info("TM Csp Master Leaf node not available")
            return False
        
        devInfo = component_manager.get_device(component_manager.input_parameter.tm_leaf_sdp_master_dev_name)
        if devInfo.faulty:
            self.logger.info("TM SDP Master Leaf node not available")
            return False
        
        subarray_count = 0
        for dev_name in component_manager.input_parameter.tm_subarray_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.faulty:
                subarray_count += 1
        if subarray_count == 0: 
            self.logger.info("No TM Subarray available")
            return False

        dish_count = 0
        for dev_name in component_manager.input_parameter.tm_dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.faulty:
                dish_count += 1
        if dish_count == 0: 
            self.logger.info("No Dish available")
            return False

        return True

    def adapter_error_message_result(self, dev_name, e):
        component_manager = self.target
        result_code = ResultCode.FAILED
        message = f"Error in creating adapter for {dev_name}: {e}"
        self.logger.error(message)
        component_manager.add_command_execution("TelescopeOn", result_code, message)
        return result_code,message

    def init_adapters(self, component_manager):
        
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
                    error_dev_names.append(dev_name)
        
        if num_working == 0:
            message = f"Error in creating tm subarray adapters {'.'.join(error_dev_names)}"
            self.logger.error(message)
            component_manager.add_command_execution("TelescopeOn", ResultCode.FAILED, message)
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
                    error_dev_names.append(dev_name)
        
        if num_working == 0:
            message = f"Error in creating dish adapters {'.'.join(error_dev_names)}"
            self.logger.error(message)
            component_manager.add_command_execution("TelescopeOn", ResultCode.FAILED, message)
            return ResultCode.FAILED, message
        
        return ResultCode.OK, ""

    def do(self):
        raise NotImplementedError("This class must be inherited!")


class TelescopeOn(AbstractTelescopeOnOff):
    """
    A class for CentralNode's TelescopeOn() command.

    TelescopeOn command on Central node enables the telescope to perform further operations
    and observations. It Invokes On command on lower level devices.

    """

    def __init__(self, target, pop_state_model, adapter_factory = AdapterFactory(), *args, logger=None, **kwargs):
        super().__init__(target, pop_state_model, adapter_factory, args, logger, kwargs)

    def do(self):
        """
        Method to invoke Telescope On command on Lower level devices.

        param argin:
            None.

        """
        component_manager = self.target

        component_manager.component.desired_telescope_state = DevState.ON
        
        ret_code, message = self.init_adapters(component_manager)
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        # send commands to sub-devices

        try:
            self.tm_leaf_csp_master_adapter.On()
        except Exception as e:
            message = f"Error in calling Telescope On in TM CSP Master Leaf {self.tm_leaf_csp_master_adapter.dev_name}: {e}"
            self.logger.error(message)
            component_manager.add_command_execution("TelescopeOn", ResultCode.FAILED, message)
            return ResultCode.FAILED, message

        try:
            self.tm_leaf_sdp_master_adapter.On()
        except Exception as e:
            message = f"Error in calling Telescope On in TM SDP Master Leaf {self.tm_leaf_sdp_master_adapter.dev_name}: {e}"
            self.logger.error(message)
            component_manager.add_command_execution("TelescopeOn", ResultCode.FAILED, message)
            return ResultCode.FAILED, message

        for adapter in self.tm_subarray_adapters:
            try:
                adapter.On()
            except Exception as e:
                message = f"Error in calling Telescope On in TM Subarray {adapter.dev_name}: {e}"
                self.logger.error(message)
                component_manager.add_command_execution("TelescopeOn", ResultCode.FAILED, message)
                return ResultCode.FAILED, message
        
        for adapter in self.tm_dish_adapters:
            try:
                adapter.SetStandbyFPMode()
            except Exception as e:
                message = f"Error in calling SetStandbyFPMode in TM Dish Leaf {adapter.dev_name}: {e}"
                self.logger.error(message)
                component_manager.add_command_execution("TelescopeOn", ResultCode.FAILED, message)
                return ResultCode.FAILED, message
            try:
                adapter.SetOperateMode()
            except Exception as e:
                message = f"Error in calling SetOperateMode in TM Dish Leaf {adapter.dev_name}: {e}"
                self.logger.error(message)
                component_manager.add_command_execution("TelescopeOn", ResultCode.FAILED, message)
                return ResultCode.FAILED, message
        
        component_manager.add_command_execution("TelescopeOn", ResultCode.OK, "")
        return (ResultCode.OK, "")



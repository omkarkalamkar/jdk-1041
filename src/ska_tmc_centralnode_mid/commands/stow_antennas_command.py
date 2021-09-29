from tango import DevState
from ska_tango_base.commands import BaseCommand
from ska_tmc_centralnode_mid.manager.adapters import AdapterFactory, AdapterType
from ska_tango_base.commands import ResultCode

class StowAntennas(BaseCommand):
    """
    A class for CentralNode's StowAntennas() command.

    Invokes the command SetStowMode on the specified receptors.

    """
    def __init__(self, target, pop_state_model, adapter_factory = AdapterFactory(), *args, logger=None, **kwargs):
        super().__init__(target, args, logger, kwargs)
        self.op_state_model = pop_state_model
        self._adapter_factory = adapter_factory
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
            self.logger.error("StowAntennas() is not allowed in current state %s", self.op_state_model.op_state)
            return False

        # for this command I need a number of sub-devices
        component_manager = self.target

        dish_count = 0
        for dev_name in component_manager.input_parameter.tm_dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if devInfo is not None and not devInfo.faulty:
                dish_count += 1
        if dish_count == 0: 
            self.logger.info("No Dish available")
            return False

        return True

    def init_adapters(self, component_manager):
        
        self.tm_dish_adapters = []

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
            component_manager.add_command_execution("StowAntennas", ResultCode.FAILED, message)
            return ResultCode.FAILED, message
        
        return ResultCode.OK, ""

    def do(self, argin):
        """
        Method to invoke StowAntennas command.

        param argin:
            List of Receptors to be stowed.

        """
        component_manager = self.target

        ret_code, message = self.init_adapters(component_manager)
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        for i in range(0, len(argin)):
            for adapter in self.tm_dish_adapters:
                if argin[i] not in adapter.dev_name:
                    continue

                try:
                    adapter.SetStowMode()
                except Exception as e:
                    message = f"Error in calling SetStowMode in TM Dish Leaf {adapter.dev_name}: {e}"
                    self.logger.error(message)
                    component_manager.add_command_execution("StowAntennas", ResultCode.FAILED, message)
                    return ResultCode.FAILED, message

        component_manager.add_command_execution("StowAntennas", ResultCode.OK, "")
        return (ResultCode.OK, "")

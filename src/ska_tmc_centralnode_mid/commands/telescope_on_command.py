from tango import DevState

from ska_tango_base.commands import BaseCommand
from ska_tango_base.commands import ResultCode
from ska_tmc_centralnode_mid.manager.adapters import AdapterType, AdapterFactory
from ska_tmc_centralnode_mid.commands.abstract_command import AbstractTelescopeOnOff

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
        
        ret_code, message = self.init_adapters("TelescopeOn", component_manager)
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        # send commands to sub-devices

        try:
            self.tm_leaf_csp_master_adapter.On()
        except Exception as e:
            return self.generate_command_result(ResultCode.FAILED, f"Error in calling Telescope On in TM CSP Master Leaf {self.tm_leaf_csp_master_adapter.dev_name}: {e}")

        try:
            self.tm_leaf_sdp_master_adapter.On()
        except Exception as e:
            return self.generate_command_result(ResultCode.FAILED, f"Error in calling Telescope On in TM SDP Master Leaf {self.tm_leaf_sdp_master_adapter.dev_name}: {e}")

        for adapter in self.tm_subarray_adapters:
            try:
                adapter.On()
            except Exception as e:
                return self.generate_command_result(ResultCode.FAILED, f"Error in calling Telescope On in TM Subarray {adapter.dev_name}: {e}")
        
        for adapter in self.tm_dish_adapters:
            try:
                adapter.SetStandbyFPMode()
            except Exception as e:
                return self.generate_command_result(ResultCode.FAILED, f"Error in calling SetStandbyFPMode in TM Dish Leaf {adapter.dev_name}: {e}")
            try:
                adapter.SetOperateMode()
            except Exception as e:
                return self.generate_command_result(ResultCode.FAILED, f"Error in calling SetOperateMode in TM Dish Leaf {adapter.dev_name}: {e}")
        
        return (ResultCode.OK, "")



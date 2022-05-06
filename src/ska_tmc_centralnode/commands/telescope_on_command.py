from ska_tango_base.commands import ResultCode
from tango import DevState

from ska_tmc_centralnode.commands.abstract_command import (
    AbstractTelescopeOnOff,
)


class TelescopeOn(AbstractTelescopeOnOff):
    """
    A class for CentralNode's TelescopeOn() command.

    TelescopeOn command on Central node enables the telescope to perform further operations
    and observations. It Invokes On command on lower level devices.

    """

    def __init__(
        self,
        target,
        pop_state_model,
        adapter_factory=None,
        timeout_mccs=3000,
        step_sleep=0.1,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(
            target, pop_state_model, adapter_factory, args, logger, kwargs
        )
        self._timeout_mccs = timeout_mccs
        self._step_sleep = step_sleep
        self.init_adapters()

    def do_mid(self, argin=None):
        """
        Method to invoke Telescope On command on Lower level devices.

        param argin:
            None.

        """
        component_manager = self.target

        component_manager.component.desired_telescope_state = DevState.ON

        for ret_code, message in [
            self.turn_on_csp(),
            self.turn_on_sdp(),
            self.turn_on_subarrays(),
            self.set_standby_fp_mode_dishes(),
            self.set_operate_mode_dishes(),
        ]:
            if ret_code == ResultCode.FAILED:
                return ret_code, message

        return (ResultCode.OK, "")

    def turn_on_sdp(self):
        return self.send_command(
            [self.tm_leaf_sdp_master_adapter],
            "Error in calling TelescopeOn() on TMC SDP Subarray leaf",
            "On",
        )

    def turn_on_csp(self):
        return self.send_command(
            [self.tm_leaf_csp_master_adapter],
            "Error in calling TelescopeOn() on TMC CSP Subarray leaf",
            "On",
        )

    def turn_on_subarrays(self):
        return self.send_command(
            self.tm_subarray_adapters,
            "Error in calling TelescopeOn() on TMC Subarray",
            "On",
        )

    def set_standby_fp_mode_dishes(self):
        return self.send_command(
            self.tm_dish_adapters,
            "Error in calling TelescopeOn() on TMC Dish leaf node",
            "SetStandbyFPMode",
        )

    def set_operate_mode_dishes(self):
        return self.send_command(
            self.tm_dish_adapters,
            "Error in calling TelescopeOn() on TMC Dish leaf node",
            "SetOperateMode",
        )

    def do_low(self, argin=None):
        """
        Method to invoke Telescope On command on Lower level devices.

        param argin:
            None.

        """
        component_manager = self.target
        component_manager.component.desired_telescope_state = DevState.ON

        # send commands to sub-devices
        # import debugpy; debugpy.debug_this_thread()
        for ret_code, message in [
            self.turn_on_mccs_master(),
            self.turn_on_mccs_subarray(),
        ]:
            if ret_code == ResultCode.FAILED:
                return ret_code, message

        return (ResultCode.OK, "")

    def turn_on_mccs_master(self):
        return self.send_command(
            [self.tm_leaf_mccs_master_adapter],
            "Error in calling TelescopeOn() in TM MCCS Master Leaf",
            "On",
        )

    def turn_on_mccs_subarray(self):
        return self.send_command(
            self.tm_subarray_adapters,
            "Error in calling TelescopeOn() in TM Subarray",
            "On",
        )

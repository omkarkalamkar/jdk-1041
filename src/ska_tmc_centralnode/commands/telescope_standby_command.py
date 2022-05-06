import time

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from tango import DevState

from ska_tmc_centralnode.commands.abstract_command import (
    AbstractTelescopeOnOff,
)


class TelescopeStandby(AbstractTelescopeOnOff):
    """
    A class for CentralNode's TelescopeStandby() command.
    """

    def __init__(
        self,
        target,
        pop_state_model,
        adapter_factory=None,
        timeout_subarrays=3000,
        step_sleep=0.1,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(
            target, pop_state_model, adapter_factory, args, logger, kwargs
        )
        self._timeout_subarrays = timeout_subarrays
        self._step_sleep = step_sleep
        self.init_adapters()

    def do_mid(self, argin=None):
        """
        Method to invoke TelescopeStandby command on Lower level devices.

        param:
            None

        return:
            none

        """
        component_manager = self.target

        component_manager.component.desired_telescope_state = DevState.STANDBY

        ret_code, message = self.turn_standby_subarrays()
        if ret_code == ResultCode.FAILED:
            return ret_code, message
        
        self.logger.info(
            "waiting for ALL Subarray devices obsState to be Empty"
        )
        all_empty = False
        start_time = time.time()
        while not all_empty:
            all_empty = True
            for adapter in self.tm_subarray_adapters:
                if (
                    not component_manager.get_device(
                        adapter.dev_name
                    ).obs_state
                    == ObsState.EMPTY
                ):
                    self.logger.error(
                        "Subarray %s still not empty", adapter.dev_name
                    )
                    all_empty = False
            elapsed_time = time.time() - start_time
            if elapsed_time > self._timeout_subarrays:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    "Timeout in waiting for subarrays devices to be empty",
                )
            time.sleep(self._step_sleep)
        
        for ret_code, message in [
            self.turn_standby_csp(),
            self.turn_standby_sdp(),
            self.set_standby_fp_mode_dishes(),
            self.set_standby_lp_mode_dishes(),
        ]:
            if ret_code == ResultCode.FAILED:
                return ret_code, message

        return (ResultCode.OK, "")

    def do_low(self, argin=None):
        """
        Method to invoke TelescopeStandby command on Lower level devices.

        param:
            None

        return:
            none

        """
        component_manager = self.target

        component_manager.component.desired_telescope_state = DevState.STANDBY

        ret_code, message = self.turn_standby_subarrays()
        if ret_code == ResultCode.FAILED:
            return ret_code, message
        self.logger.info(
            "waiting for ALL Subarray devices obsState to be Empty"
        )
        all_empty = False
        start_time = time.time()
        while not all_empty:
            all_empty = True
            for adapter in self.tm_subarray_adapters:
                if (
                    not component_manager.get_device(
                        adapter.dev_name
                    ).obs_state
                    == ObsState.EMPTY
                ):
                    self.logger.error(
                        "Subarray %s still not empty", adapter.dev_name
                    )
                    all_empty = False
            elapsed_time = time.time() - start_time
            if elapsed_time > self._timeout_subarrays:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    "Timeout in waiting for subarrays devices to be empty",
                )
            time.sleep(self._step_sleep)

        ret_code, message = self.turn_standby_mccs()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        return (ResultCode.OK, "")

    def turn_standby_subarrays(self):
        return self.send_command(
            self.tm_subarray_adapters,
            "Error in calling Standby() on TMC SDP Subarray leaf",
            "Standby",
        )

    def turn_standby_sdp(self):
        return self.send_command(
            [self.tm_leaf_sdp_master_adapter],
            "Error in calling Standby() on TMC SDP Subarray leaf",
            "Standby",
        )

    def turn_standby_csp(self):
        return self.send_command(
            [self.tm_leaf_csp_master_adapter],
            "Error in calling Standby() on TMC SDP Subarray leaf",
            "Standby",
        )

    def turn_standby_mccs(self):
        return self.send_command(
            [self.tm_leaf_mccs_master_adapter],
            "Error in calling Standby() on TMC MCCS Master Device",
            "Standby",
        )

    def set_standby_fp_mode_dishes(self):
        return self.send_command(
            self.tm_dish_adapters,
            "Error in calling SetStandbyFPMode() on TMC SDP Subarray leaf",
            "SetStandbyFPMode",
        )

    def set_standby_lp_mode_dishes(self):
        return self.send_command(
            self.tm_dish_adapters,
            "Error in calling SetStandbyLPMode() on TMC SDP Subarray leaf",
            "SetStandbyLPMode",
        )

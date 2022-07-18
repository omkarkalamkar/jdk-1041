import time

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from tango import DevState

from ska_tmc_centralnode.commands.abstract_command import (
    AbstractTelescopeOnOff,
)


class TelescopeOff(AbstractTelescopeOnOff):
    """
    A class for CentralNode's TelescopeOff() command. Sets the CentralNode into telescopestate to OFF.
    """

    def __init__(
        self,
        target,
        pop_state_model,
        adapter_factory=None,
        timeout_subarrays=3,
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
        Method to invoke telescopeoff command on Lower level devices.
        param:
            None

        return:
            A tuple containing a return code and a string message indicating status.

        rtype:
            (ResultCode, str)

        """
        # component_manager = self.target
        self.component_manager.component.desired_telescope_state = DevState.OFF

        ret_code, message = self.turn_off_subarrays()
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
                    not self.component_manager.get_device(
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
            self.turn_off_csp(),
            self.turn_off_sdp(),
            self.turn_off_subarrays(),
            self.set_standby_fp_mode_dishes(),
            self.set_standby_lp_mode_dishes(),
        ]:
            if ret_code == ResultCode.FAILED:
                return ret_code, message

        return (ResultCode.OK, "")

    def turn_off_csp(self):
        return self.send_command(
            [self.tm_leaf_csp_master_adapter],
            "Error in calling TelescopeOff() on TMC CSP Subarray leaf",
            "Off",
        )

    def turn_off_sdp(self):
        return self.send_command(
            [self.tm_leaf_sdp_master_adapter],
            "Error in calling TelescopeOff() on TMC SDP Subarray leaf",
            "Off",
        )

    def turn_off_subarrays(self):
        return self.send_command(
            self.tm_subarray_adapters,
            "Error in calling TelescopeOff() in TM Subarray",
            "Off",
        )

    def set_standby_fp_mode_dishes(self):
        return self.send_command(
            self.tm_dish_adapters,
            "Error in calling TelescopeOff() on TMC Dish leaf node",
            "SetStandbyFPMode",
        )

    def set_standby_lp_mode_dishes(self):
        return self.send_command(
            self.tm_dish_adapters,
            "Error in calling TelescopeOff() on TMC Dish leaf node",
            "SetStandbyLPMode",
        )

    def do_low(self, argin=None):
        """
        Method to invoke telescopeoff command on Lower level devices.
        param:
            None

        return:
            A tuple containing a return code and a string message indicating status.

        rtype:
            (ResultCode, str)

        """
        # component_manager = self.target
        self.component_manager.component.desired_telescope_state = DevState.OFF

        ret_code, message = self.turn_off_subarrays()
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
                    not self.component_manager.get_device(
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

        ret_code, message = self.turn_off_mccs_mln()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        return (ResultCode.OK, "")

    def turn_off_mccs_mln(self):
        return self.send_command(
            [self.tm_leaf_mccs_master_adapter],
            "Error in calling TelescopeOff() in TM MCCS Master Leaf",
            "Off",
        )

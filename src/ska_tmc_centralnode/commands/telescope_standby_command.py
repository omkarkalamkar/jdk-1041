import time

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from tango import DevState

from ska_tmc_centralnode.commands.abstract_command import (
    AbstractTelescopeOnOff,
)
from ska_tmc_centralnode.manager.adapters import AdapterFactory


class TelescopeStandby(AbstractTelescopeOnOff):
    """
    A class for CentralNode's TelescopeStandby() command.
    """

    def __init__(
        self,
        target,
        pop_state_model,
        adapter_factory=AdapterFactory(),
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

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        for adapter in self.tm_subarray_adapters:
            try:
                adapter.StandBy()
            except Exception as e:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    f"Error in calling Telescope StandBy in TM Subarray {adapter.dev_name}: {e}",
                )

        self.logger.info(
            "waiting for ALL Subarray devices obsState to be Empty"
        )
        all_empty = False
        start_time = time.time()
        while not all_empty:
            all_empty = True
            for adapter in self.tm_subarray_adapters:
                if (
                    not component_manager.get_device(adapter.dev_name).obsState
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

        try:
            self.tm_leaf_csp_master_adapter.StandBy()
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                "Error in calling Telescope StandBy in TM CSP Master"
                + f" Leaf {self.tm_leaf_csp_master_adapter.dev_name}: {e}",
            )

        try:
            self.tm_leaf_sdp_master_adapter.StandBy()
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                "Error in calling Telescope StandBy in TM SDP Master"
                + f" Leaf {self.tm_leaf_sdp_master_adapter.dev_name}: {e}",
            )

        for adapter in self.tm_dish_adapters:
            try:
                adapter.SetStandbyFPMode()
            except Exception as e:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    f"Error in calling SetStandbyFPMode in TM Dish Leaf {adapter.dev_name}: {e}",
                )

            try:
                adapter.SetStandbyLPMode()
            except Exception as e:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    f"Error in calling SetStandbyLPMode in TM Dish Leaf {adapter.dev_name}: {e}",
                )

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

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        for adapter in self.tm_subarray_adapters:
            try:
                adapter.StandBy()
            except Exception as e:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    f"Error in calling Telescope StandBy in TM Subarray {adapter.dev_name}: {e}",
                )

        self.logger.info(
            "waiting for ALL Subarray devices obsState to be Empty"
        )
        all_empty = False
        start_time = time.time()
        while not all_empty:
            all_empty = True
            for adapter in self.tm_subarray_adapters:
                if (
                    not component_manager.get_device(adapter.dev_name).obsState
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

        try:
            self.tm_leaf_mccs_master_adapter.StandBy()
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                "Error in calling Telescope StandBy in TM CSP Master"
                + f" Leaf {self.tm_leaf_mccs_master_adapter.dev_name}: {e}",
            )

        return (ResultCode.OK, "")

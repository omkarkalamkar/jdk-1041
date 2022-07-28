import threading
import time
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
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
        component_manager,
        adapter_factory=None,
        timeout_subarrays=3,
        step_sleep=0.1,
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self._timeout_subarrays = timeout_subarrays
        self._step_sleep = step_sleep

    def telescope_standby(
        self,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):

        """This is a long running method for TelescopeStandby command, it executes do hook,
        invokes TelescopeStandby command on lower level devices.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)

        ret_code, message = self.do(argin=None)
        self.logger.info(message)
        if ret_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=ResultCode.FAILED,
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=ResultCode.OK,
            )

    def do_mid(self, argin=None):
        """
        Method to invoke TelescopeStandby command on SubarrayNode, CSP and SDP
        Master Leaf Nodes. Also to invoke StandbyFP and then StandbyLP commands
        on Dish Leaf Nodes.

        param:
            None

        return:
            A tuple containing a return code and a message

        """
        self.component_manager.component.desired_telescope_state = (
            DevState.STANDBY
        )
        self.logger.info(
            "Invoking TelescopeStandby command on the lower level devices"
        )

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

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
            self.turn_standby_csp(),
            self.turn_standby_sdp(),
            self.set_standby_fp_mode_dishes(),
            self.set_standby_lp_mode_dishes(),
        ]:
            if ret_code == ResultCode.FAILED:
                return ret_code, message

        self.logger.info(
            "TelescopeStandby command is completed successfully on the CentralNode"
        )
        return (ResultCode.OK, "")

    def do_low(self, argin=None):
        """
        Method to invoke TelescopeStandby command on SubarrayNode and MCCS
        Master Leaf Node.

        param:
            None

        return:
            A tuple containing a return code and a message

        """
        self.component_manager.component.desired_telescope_state = (
            DevState.STANDBY
        )

        self.logger.info(
            "Invoking TelescopeStandby command on the lower level devices"
        )

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

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

        ret_code, message = self.turn_standby_mccs()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        self.logger.info(
            "TelescopeStandby command is completed successfully on the CentralNode"
        )
        return (ResultCode.OK, "")

    def turn_standby_subarrays(self):
        self.logger.info(
            f"Standby command on TMC SubarrayNode devices: {self.tm_subarray_adapters}"
        )
        return self.send_command(
            self.tm_subarray_adapters,
            f"Error in calling Standby() on TMC SubarrayNode devices: {self.tm_subarray_adapters}",
            "Standby",
        )

    def turn_standby_sdp(self):
        self.logger.info(
            f"Standby command on {self.tm_leaf_sdp_master_adapter.dev_name}"
        )
        return self.send_command(
            [self.tm_leaf_sdp_master_adapter],
            f"Error in calling Standby() on {self.tm_leaf_sdp_master_adapter.dev_name}",
            "Standby",
        )

    def turn_standby_csp(self):
        self.logger.info(
            f"Standby command on {self.tm_leaf_csp_master_adapter.dev_name}"
        )
        return self.send_command(
            [self.tm_leaf_csp_master_adapter],
            f"Error in calling Standby() on {self.tm_leaf_csp_master_adapter.dev_name}",
            "Standby",
        )

    def turn_standby_mccs(self):
        self.logger.info(
            f"Standby command on  {self.tm_leaf_mccs_master_adapter.dev_name}"
        )
        return self.send_command(
            [self.tm_leaf_mccs_master_adapter],
            f"Error in calling Standby() on {self.tm_leaf_mccs_master_adapter.dev_name}",
            "Standby",
        )

    def set_standby_fp_mode_dishes(self):
        self.logger.info(
            f"SetStandbyFPMode command on Dish Leaf Nodes: {self.tm_dish_adapters}"
        )
        return self.send_command(
            self.tm_dish_adapters,
            f"Error in calling SetStandbyFPMode() on Dish Leaf Nodes: {self.tm_dish_adapters}",
            "SetStandbyFPMode",
        )

    def set_standby_lp_mode_dishes(self):
        self.logger.info(
            f"SetStandbyLPMode command on Dish Leaf Nodes: {self.tm_dish_adapters}"
        )
        return self.send_command(
            self.tm_dish_adapters,
            f"Error in calling SetStandbyLPMode() on Dish Leaf Nodes: {self.tm_dish_adapters}",
            "SetStandbyLPMode",
        )

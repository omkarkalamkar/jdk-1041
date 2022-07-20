import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
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
        component_manager,
        adapter_factory=None,
        timeout_mccs=3,
        step_sleep=0.1,
        logger=None,
        *args,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, *args, logger, **kwargs
        )
        self._timeout_mccs = timeout_mccs
        self._step_sleep = step_sleep
        self.init_adapters()

    def telescope_off(
        self,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):

        """This is a long running method

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        # if task_callback:
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
        Method to invoke telescopeoff command on Lower level devices.
        param:
            None

        return:
            A tuple containing a return code and a string message indicating status.

        rtype:
            (ResultCode, str)

        """
        self.component_manager.component.desired_telescope_state = DevState.OFF
        print(
            "Component.desired telescope state is::::::",
            self.component_manager.component.desired_telescope_state,
        )
        print("Invoking TelescopeOff command on the lower level devices")
        for ret_code, message in [
            self.turn_on_csp(),
            self.turn_on_sdp(),
            self.turn_on_subarrays(),
            self.set_standby_fp_mode_dishes(),
            self.set_operate_mode_dishes(),
        ]:
            if ret_code == ResultCode.FAILED:
                return ret_code, message
        print(
            "do_mid for TelescopeOff command on the lower level devices is successful"
        )
        return (ResultCode.OK, "")

        # ret_code, message = self.turn_off_subarrays()
        # if ret_code == ResultCode.FAILED:
        #     return ret_code, message

        # self.logger.info(
        #     "waiting for ALL Subarray devices obsState to be Empty"
        # )
        # all_empty = False
        # start_time = time.time()
        # while not all_empty:
        #     all_empty = True
        #     for adapter in self.tm_subarray_adapters:
        #         if (
        #             not self.component_manager.get_device(
        #                 adapter.dev_name
        #             ).obs_state
        #             == ObsState.EMPTY
        #         ):
        #             self.logger.error(
        #                 "Subarray %s still not empty", adapter.dev_name
        #             )
        #             all_empty = False
        #     elapsed_time = time.time() - start_time
        #     if elapsed_time > self._timeout_subarrays:
        #         return self.generate_command_result(
        #             ResultCode.FAILED,
        #             "Timeout in waiting for subarrays devices to be empty",
        #         )
        #     time.sleep(self._step_sleep)
        #     self.set_standby_fp_mode_dishes(),
        #     self.set_operate_mode_dishes(),
        # ]:
        #     if ret_code == ResultCode.FAILED:
        #         return ret_code, message
        # print(
        #     "do_mid for TelescopeOff command on the lower level devices is successful"
        # )
        # return (ResultCode.OK, "")

        # ret_code, message = self.turn_off_subarrays()
        # if ret_code == ResultCode.FAILED:
        #     return ret_code, message

        # self.logger.info(
        #     "waiting for ALL Subarray devices obsState to be Empty"
        # )
        # all_empty = False
        # start_time = time.time()
        # while not all_empty:
        #     all_empty = True
        #     for adapter in self.tm_subarray_adapters:
        #         if (
        #             not self.component_manager.get_device(
        #                 adapter.dev_name
        #             ).obs_state
        #             == ObsState.EMPTY
        #         ):
        #             self.logger.error(
        #                 "Subarray %s still not empty", adapter.dev_name
        #             )
        #             all_empty = False
        #     elapsed_time = time.time() - start_time
        #     if elapsed_time > self._timeout_subarrays:
        #         return self.generate_command_result(
        #             ResultCode.FAILED,
        #             "Timeout in waiting for subarrays devices to be empty",
        #         )
        #     time.sleep(self._step_sleep)

        # for ret_code, message in [
        #     self.turn_off_csp(),
        #     self.turn_off_sdp(),
        #     self.turn_off_subarrays(),
        #     self.set_standby_fp_mode_dishes(),
        #     self.set_standby_lp_mode_dishes(),
        # ]:
        #     if ret_code == ResultCode.FAILED:
        #         return ret_code, message

        # return (ResultCode.OK, "")

    def turn_off_csp(self):
        print("Telescopeoff for Csp devices")
        return self.send_command(
            [self.tm_leaf_csp_master_adapter],
            f"Error in calling Off() command for {self.tm_leaf_csp_master_adapter}",
            "Off",
        )

    def turn_off_sdp(self):
        print("Telescopeoff for Sdp devices")
        return self.send_command(
            [self.tm_leaf_sdp_master_adapter],
            f"Error in calling Off() command for {self.tm_leaf_sdp_master_adapter}",
            "Off",
        )

    def turn_off_subarrays(self):
        print("Telescopeoff for tm subarrays devices")
        return self.send_command(
            self.tm_subarray_adapters,
            f"Error in calling Off() for {self.tm_subarray_adapters}",
            "Off",
        )

    def set_standby_fp_mode_dishes(self):
        print("TelescopeOff for dish devices")
        return self.send_command(
            self.tm_dish_adapters,
            f"Error in calling SetStandbyFPMode() command for {self.tm_dish_adapters}",
            "SetStandbyFPMode",
        )

    def set_standby_lp_mode_dishes(self):
        print("TelescopeOff for dish devices")
        return self.send_command(
            self.tm_dish_adapters,
            f"Error in calling SetStandbyLPMode()command for {self.tm_dish_adapters}",
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
        self.component_manager.component.desired_telescope_state = DevState.OFF

        for ret_code, message in [
            self.turn_on_mccs_master(),
            self.turn_on_subarrays(),
        ]:
            if ret_code == ResultCode.FAILED:
                return ret_code, message

        return (ResultCode.OK, "")

        # ret_code, message = self.turn_off_subarrays()
        # if ret_code == ResultCode.FAILED:
        #     return ret_code, message

        # self.logger.info(
        #     "waiting for ALL Subarray devices obsState to be Empty"
        # )
        # all_empty = False
        # start_time = time.time()
        # while not all_empty:
        #     all_empty = True
        #     for adapter in self.tm_subarray_adapters:
        #         if (
        #             not self.component_manager.get_device(
        #                 adapter.dev_name
        #             ).obs_state
        #             == ObsState.EMPTY
        #         ):
        #             self.logger.error(
        #                 "Subarray %s still not empty", adapter.dev_name
        #             )
        #             all_empty = False
        #     elapsed_time = time.time() - start_time
        #     if elapsed_time > self._timeout_subarrays:
        #         return self.generate_command_result(
        #             ResultCode.FAILED,
        #             "Timeout in waiting for subarrays devices to be empty",
        #         )
        #     time.sleep(self._step_sleep)

        # ret_code, message = self.turn_off_mccs_mln()
        # if ret_code == ResultCode.FAILED:
        #     return ret_code, message

        # return (ResultCode.OK, "")

    def turn_off_mccs_mln(self):
        return self.send_command(
            [self.tm_leaf_mccs_master_adapter],
            "Error in calling TelescopeOff() in TM MCCS Master Leaf",
            "Off",
        )

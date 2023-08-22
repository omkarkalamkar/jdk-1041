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


class TelescopeOff(AbstractTelescopeOnOff):
    """
    A class for CentralNode's TelescopeOff() command. Sets the CentralNode into telescopestate to OFF.
    """

    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        timeout_subarrays=3,
        step_sleep=0.1,
        logger=None,
        *args,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self._timeout_subarrays = timeout_subarrays
        self._step_sleep = step_sleep

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

        task_callback(status=TaskStatus.IN_PROGRESS)

        return_code, message = self.do(argin=None)
        self.logger.info(message)
        if return_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
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

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOff command"
        )

        return_codes, message_or_unique_ids = self.turn_off_subarrays()
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

        self.logger.info(
            "waiting for ALL Subarray devices obsState to be Empty"
        )
        all_empty = False
        start_time = time.time()
        while not all_empty:
            all_empty = True
            for adapter in self.subarray_adapters:
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
                return (
                    ResultCode.FAILED,
                    "Timeout in waiting for subarrays devices to be empty",
                )
            time.sleep(self._step_sleep)

        unavailable_devices = []
        for return_codes, message_or_unique_ids in [
            self.turn_off_dishes(),
            self.turn_off_csp(),
            self.turn_off_sdp(),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                # condition for exception raised during invoking command
                if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                    return ResultCode.FAILED, message_or_unique_id
                # condition for unavailable devices
                elif return_code in [ResultCode.REJECTED]:
                    # return ResultCode.FAILED, message_or_unique_id
                    unavailable_devices.append(
                        message_or_unique_id.split(" ")[0]
                    )

        if unavailable_devices:
            self.logger.info(f"Unavailable devices are {unavailable_devices}")
            return (
                ResultCode.FAILED,
                f"Unavailable devices are {unavailable_devices}",
            )

        return (ResultCode.OK, "")

    def turn_off_csp(self):
        self.logger.info(
            f"Invoking TelescopeOff command for {self.csp_mln_adapter.dev_name} devices"
        )
        if self.component_manager.check_if_csp_mln_is_available() is True:
            return self.send_command(
                [self.csp_mln_adapter],
                f"Error in calling Off command for {self.csp_mln_adapter.dev_name}",
                "Off",
            )
        else:
            return (
                [ResultCode.FAILED],
                [
                    f"{self.csp_mln_adapter.dev_name} is not available to receive command"
                ],
            )

    def turn_off_sdp(self):
        self.logger.info(
            f"Invoking TelescopeOff command for {self.sdp_mln_adapter.dev_name} devices"
        )
        if self.component_manager.check_if_sdp_mln_is_available() is True:
            return self.send_command(
                [self.sdp_mln_adapter],
                f"Error in calling Off command for {self.sdp_mln_adapter.dev_name}",
                "Off",
            )
        else:
            return (
                [ResultCode.FAILED],
                [
                    f"{self.sdp_mln_adapter.dev_name} is not available to receive command"
                ],
            )

    def turn_off_subarrays(self):
        self.logger.info(
            f"Invoking TelescopeOff command for {self.subarray_adapters} devices"
        )
        return self.send_command(
            self.subarray_adapters,
            f"Error in calling Off command for {self.subarray_adapters}",
            "Off",
        )

    def turn_off_dishes(self):
        return self.send_command(
            self.dish_adapters,
            "Error in calling TelescopeOff() on TMC Dish leaf node",
            "Off",
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

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOff command"
        )

        return_codes, message_or_unique_ids = self.turn_off_subarrays()
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

        self.logger.info(
            """Waiting for all the Subarray devices to be in EMPTY
            observation state"""
        )
        all_empty = False
        start_time = time.time()
        while not all_empty:
            all_empty = True
            for adapter in self.subarray_adapters:
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
                return (
                    ResultCode.FAILED,
                    """Timeout in waiting for the subarray devices to be in
                    EMPTY observation state""",
                )
            time.sleep(self._step_sleep)

        unavailable_devices = []
        for return_codes, message_or_unique_ids in [
            # self.turn_off_mccs_mln(),
            self.turn_off_csp(),
            self.turn_off_sdp(),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                # condition for exception raised during invoking command
                if return_code in [ResultCode.FAILED]:
                    return ResultCode.FAILED, message_or_unique_id
                # condition for unavailable devices
                elif return_code in [ResultCode.REJECTED]:
                    # return ResultCode.FAILED, message_or_unique_id
                    unavailable_devices.append(
                        message_or_unique_id.split(" ")[0]
                    )

        if unavailable_devices:
            self.logger.info(f"Unavailable devices are {unavailable_devices}")
            return (
                ResultCode.FAILED,
                f"Unavailable devices are {unavailable_devices}",
            )

    # def turn_off_mccs_mln(self):
    #     return self.send_command(
    #         [self.tm_leaf_mccs_master_adapter],
    #         f"Error in calling TelescopeOff() for {self.tm_leaf_mccs_master_adapter}",
    #         "Off",
    #     )

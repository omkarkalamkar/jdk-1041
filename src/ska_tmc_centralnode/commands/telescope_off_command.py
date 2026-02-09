"""Command class for TelescopeOff()"""

import logging
import threading
import time
from typing import Callable, List, Optional, Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from tango import DevState

from ska_tmc_centralnode.commands.central_node_command import TelescopeOnOff


class TelescopeOff(TelescopeOnOff):
    """
    A class for CentralNode's TelescopeOff() command. Sets the
    CentralNode into telescopeState to OFF.
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
        # pylint:disable=keyword-arg-before-vararg
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self._timeout_subarrays = timeout_subarrays
        self._step_sleep = step_sleep

    def telescope_off(
        self,
        logger: logging.Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> Tuple[ResultCode, str]:
        """
        This is a long running method

        Args:
            logger: logger
            task_callback: Update task state, defaults to None
            task_abort_event: Check for abort, defaults to None
            task_abort_event: Event, optional

        """

        task_callback(status=TaskStatus.IN_PROGRESS)

        return_code, message = self.do(argin=None)
        self.logger.info(message)
        if return_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, message),
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED, result=(ResultCode.OK, message)
            )
        # return return_code, message

    def do_mid(self, argin=None) -> Tuple[ResultCode, str]:
        """
        Method to invoke Off command on lower level devices.

        Args:
            argin (str): Default is None.

        Returns:
            Tuple(ResultCode, str): tuple containing a return code
            and a string message indicating status.

        """
        self.component_manager.component.desired_telescope_state = DevState.OFF

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOff command."
        )

        self.logger.info(
            "Invoking Off command on the lower level devices",
        )

        return_codes, message_or_unique_ids = self.turn_off_subarrays()
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

        self.logger.debug(
            "Waiting for all subarray devices to reach the EMPTY "
            "observation state."
        )
        all_empty = False
        start_time = time.time()
        while not all_empty:
            all_empty = True
            for adapter in self.subarray_adapters:
                obs_state = self.component_manager.get_device(
                    adapter.dev_name
                ).obs_state
                if obs_state != ObsState.EMPTY:
                    self.logger.error(
                        "Subarray current ObsState %s, while "
                        "waiting for ObsState.EMPTY. ",
                        str(obs_state),
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
                if return_code == ResultCode.FAILED:
                    return ResultCode.FAILED, message_or_unique_id
                if return_code == ResultCode.REJECTED:
                    unavailable_devices.append(
                        message_or_unique_id.split(" ")[0]
                    )

        if unavailable_devices:
            self.logger.info("Unavailable devices: %s", unavailable_devices)
            return ResultCode.OK, f"Unavailable devices: {unavailable_devices}"

        return (ResultCode.OK, "Command Completed")

    def turn_off_csp(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turn off the CSP devices

        Returns:
            Tuple(List, List): Tuple containing
            list of ResultCodes and list of messages

        """
        self.logger.info(
            "Invoking Off command on: %s",
            self.csp_mln_adapter.dev_name,
        )
        if self.component_manager.check_if_csp_mln_is_available():
            return self.send_command(
                [self.csp_mln_adapter],
                f"Error in calling Off command for "
                f"{self.csp_mln_adapter.dev_name}",
                "Off",
            )
        return [ResultCode.REJECTED], [
            f"{self.csp_mln_adapter.dev_name} "
            "is not available to receive Off command"
        ]

    def turn_off_sdp(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turn off the SDP devices

        Returns:
            Tuple(List, List): Tuple containing
            list of ResultCodes and list of messages

        """
        self.logger.info(
            "Invoking Off command on: %s",
            self.sdp_mln_adapter.dev_name,
        )
        if self.component_manager.check_if_sdp_mln_is_available():
            return self.send_command(
                [self.sdp_mln_adapter],
                f"Error in calling Off command for "
                f"{self.sdp_mln_adapter.dev_name}",
                "Off",
            )
        return [ResultCode.REJECTED], [
            f"{self.sdp_mln_adapter.dev_name} "
            "is not available to receive Off command"
        ]

    def turn_off_subarrays(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turn off the subarrays

        Returns:
            Tuple(List, List): tuple containing list of ReturnCodes
            and list of string message indicating status.

        """
        self.logger.info(
            "Invoking Off command on: %s",
            [str(adapter.dev_name) for adapter in self.subarray_adapters],
        )

        return self.send_command(
            self.subarray_adapters,
            "Error in calling Off command for subarray devices",
            "Off",
        )

    def turn_off_dishes(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turn off the dishes

        Returns:
            Tuple(List, List): tuple containing list of ReturnCodes
            and list of string message indicating status.

        """
        self.logger.info(
            "Invoking Off command on: %s",
            [str(adapter.dev_name) for adapter in self.dish_adapters],
        )
        return self.send_command(
            self.dish_adapters,
            "Error in calling Off command for dish devices",
            "Off",
        )

    def do_low(self, argin=None) -> Tuple[ResultCode, str]:
        """
        Method to invoke Off command on lower level devices.

        Args:
            argin (Str): Default is None.

        Returns:
            Tuple(ResultCode, str): tuple containing a return code
            and a string message indicating status.

        """
        self.component_manager.component.desired_telescope_state = DevState.OFF
        self.logger.info(
            "Invoking Off command on the lower level devices",
        )

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOff command."
        )
        self.logger.info(
            "Invoking Off command on the lower level devices",
        )
        return_codes, message_or_unique_ids = self.turn_off_subarrays()
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

        self.logger.debug(
            "Waiting for all subarray devices to reach the "
            "EMPTY observation state."
        )
        all_empty = False
        start_time = time.time()
        while not all_empty:
            all_empty = True
            for adapter in self.subarray_adapters:
                obs_state = self.component_manager.get_device(
                    adapter.dev_name
                ).obs_state
                if obs_state != ObsState.EMPTY:
                    self.logger.debug(
                        "Subarray %s is still not empty, current state: %s",
                        adapter.dev_name,
                        str(obs_state),
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
            self.turn_off_mccs(),
            self.turn_off_csp(),
            self.turn_off_sdp(),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                if return_code == ResultCode.FAILED:
                    return ResultCode.FAILED, message_or_unique_id
                if return_code == ResultCode.REJECTED:
                    unavailable_devices.append(
                        message_or_unique_id.split(" ")[0]
                    )

        if unavailable_devices:
            self.logger.info("Unavailable devices: %s", unavailable_devices)
            return ResultCode.OK, f"Unavailable devices: {unavailable_devices}"

        return (ResultCode.OK, "Command Completed")

    def turn_off_mccs(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turn off the MCCS devices

        Returns:
            Tuple(List, List): Tuple of list of Resultcodes
            and list of messages.

        """
        self.logger.info(
            "Invoking Off command on: %s",
            self.mccs_mln_adapter.dev_name,
        )
        if self.component_manager.check_if_mccs_mln_is_available():
            return self.send_command(
                [self.mccs_mln_adapter],
                f"Error in calling Off command for "
                f"{self.mccs_mln_adapter.dev_name}",
                "Off",
            )
        return [ResultCode.REJECTED], [
            f"{self.mccs_mln_adapter.dev_name} is not available "
            "to receive Off command"
        ]

    def update_task_status(self):
        """Updates task status implemented to"""

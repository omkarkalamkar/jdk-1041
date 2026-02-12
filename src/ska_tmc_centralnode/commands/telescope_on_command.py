"""Command class for TelescopeOn()"""

import logging
import threading
from typing import Callable, List, Optional, Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode
from tango import DevState

from ska_tmc_centralnode.commands.central_node_command import TelescopeOnOff


class TelescopeOn(TelescopeOnOff):
    """
    A class for CentralNode's TelescopeOn() command.

    TelescopeOn command on Central node enables the telescope to perform
    further operations
    and observations. It Invokes On command on lower level devices.
    """

    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        timeout_mccs=3,
        step_sleep=0.1,
        *args,
        logger=None,
        **kwargs,
    ):
        # pylint:disable=keyword-arg-before-vararg
        super().__init__(
            component_manager, adapter_factory, *args, logger=logger, **kwargs
        )

    def telescope_on(
        self,
        logger: logging.Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ) -> Tuple[ResultCode, str]:
        """
        This is a long running method for TelescopeOn command,
        it executes do hook,
        invokes TelescopeOn command on lowe level devices.

        Args:
            logger: logger
            task_callback: Update task state, defaults to None
            task_abort_event: Check for abort, defaults to None

        """
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)

        result_code, message = self.do(argin=None)
        self.logger.info(message)
        if result_code == ResultCode.FAILED:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, message),
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, message),
            )

        return result_code, message

    def do_mid(self, argin=None) -> Tuple[ResultCode, str]:
        """
        Method to invoke On command on Lower level devices.

        Args:
            argin (str): Defaults to None in case of TelescopeOn.

        Returns:
            Tuple(ResultCode, str): tuple containing a return code
            and a string message indicating status.

        """
        self.component_manager.component.desired_telescope_state = DevState.ON

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOn command"
        )

        self.logger.info("Invoking On command on the lower level devices")

        unavailable_devices = []
        for return_codes, message_or_unique_ids in [
            self.set_standby_fp_mode_dishes(),
            self.turn_on_csp(),
            self.turn_on_sdp(),
            self.turn_on_subarrays(),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                # condition for exception raised during invoking command
                if return_code in [ResultCode.FAILED]:
                    return ResultCode.FAILED, message_or_unique_id
                # condition for unavailable devices
                if return_code in [ResultCode.REJECTED]:
                    # return ResultCode.FAILED, message_or_unique_id
                    unavailable_devices.append(
                        message_or_unique_id.split(" ")[0]
                    )

        if unavailable_devices:
            self.logger.info(
                "Unavailable devices are %s ", unavailable_devices
            )
            return (
                ResultCode.OK,
                f"Unavailable devices are {unavailable_devices}",
            )

        return (ResultCode.OK, "Command Completed")

    def turn_on_sdp(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turns on the SDP

        Returns:
            Tuple(List, List): Tuple containing list of return codes
            and list of string message indicating status.

        """
        self.logger.info(
            "Invoking On command on: %s ", self.sdp_mln_adapter.dev_name
        )
        if self.component_manager.check_if_sdp_mln_is_available() is True:
            return self.send_command(
                [self.sdp_mln_adapter],
                f"Error in calling On command for\
                      {self.sdp_mln_adapter.dev_name}",
                "On",
            )

        return (
            [ResultCode.REJECTED],
            [
                self.sdp_mln_adapter.dev_name
                + " is not available to receive On command"
            ],
        )

    def turn_on_csp(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turns on the csp

        Returns:
            Tuple(List, List): A tuple containing list of
            return codes and list of string message
            indicating status.

        """
        self.logger.info(
            "Invoking On command on: %s ", self.csp_mln_adapter.dev_name
        )
        if self.component_manager.check_if_csp_mln_is_available() is True:
            return self.send_command(
                [self.csp_mln_adapter],
                "Error in calling On command for"
                + self.csp_mln_adapter.dev_name,
                "On",
            )
        return (
            [ResultCode.REJECTED],
            [
                f"{self.csp_mln_adapter.dev_name} is not available to receive"
                + " On command"
            ],
        )

    def turn_on_subarrays(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turns on the subarrays

        Returns:
            Tuple(List, List): Tuple containing list of return codes
            and list of string message indicating status.

        """
        self.logger.info(
            "Invoking On command on: %s",
            [str(adapter.dev_name) for adapter in self.subarray_adapters],
        )

        return self.send_command(
            self.subarray_adapters,
            f"Error in calling On command for {self.subarray_adapters}",
            "On",
        )

    def set_standby_fp_mode_dishes(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Sets standby fb mode in dishes

        Returns:
            Tuple(List, List): Tuple containing list of return codes
            and list of string message indicating status.

        """
        invoke_on_adapters = []
        for adapter in self.dish_adapters:
            if adapter.dishMode != DishMode.STANDBY_FP:
                invoke_on_adapters.append(adapter)

        return self.send_command(
            invoke_on_adapters,
            "Error in calling SetStandbyFPMode()"
            f" command on {invoke_on_adapters}",
            "SetStandbyFPMode",
        )

    def do_low(self, argin=None) -> Tuple[ResultCode, str]:
        """
        Method to invoke On command on Lower level devices.

        Args:
            argin (str): Default to None in case of TelescopeOn.

        Returns:
            Tuple(ReSultCode, str): Tuple containing a return code
            and a string message indicating status.

        """
        self.component_manager.component.desired_telescope_state = DevState.ON

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOn command"
        )
        self.logger.info(
            "Invoking On command on the lower level devices",
        )
        # send commands to sub-devices
        # import debugpy; debugpy.debug_this_thread()
        unavailable_devices = []
        for return_codes, message_or_unique_ids in [
            self.turn_on_mccs(),
            self.turn_on_subarrays(),
            self.turn_on_csp(),
            self.turn_on_sdp(),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                # condition for exception raised during invoking command
                if return_code in [ResultCode.FAILED]:
                    return ResultCode.FAILED, message_or_unique_id
                # condition for unavailable devices
                if return_code in [ResultCode.REJECTED]:
                    # return ResultCode.FAILED, message_or_unique_id
                    unavailable_devices.append(
                        message_or_unique_id.split(" ")[0]
                    )

        if unavailable_devices:
            self.logger.info(
                "Unavailable devices are: %s", unavailable_devices
            )
            return (
                ResultCode.OK,
                f"Unavailable devices are {unavailable_devices}",
            )

        return (ResultCode.OK, "Command Completed")

    def turn_on_mccs(self) -> Tuple[List[ResultCode], List[str]]:
        """
        Turns on the MCCS

        Returns:
            Tuple(List, List): Tuple containing list of ResultCodes
            and list of messages

        """
        self.logger.info(
            "Invoking On command on: %s ", self.mccs_mln_adapter.dev_name
        )
        if self.component_manager.check_if_mccs_mln_is_available() is True:
            return self.send_command(
                [self.mccs_mln_adapter],
                "Error in calling On command for "
                f"{self.mccs_mln_adapter.dev_name}",
                "On",
            )
        return (
            [ResultCode.REJECTED],
            [
                f"{self.mccs_mln_adapter.dev_name} is not available to "
                "receive On command"
            ],
        )

    def update_task_status(self):
        """Updates task status implemented to"""

"""Command class for TelescopeOn()"""

import threading
from typing import List, Optional, Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.type_hints import TaskCallbackType
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
        task_callback: TaskCallbackType,
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
        if task_abort_event:
            self.task_abort_event = task_abort_event
        # Indicate that the task has started
        task_callback(status=TaskStatus.IN_PROGRESS)
        self.logger.info(
            "Command ID: %s | Executing TelescopeOn command",
            self.component_manager.command_id,
        )
        result_code, message = self.do(argin=None)
        self.logger.info(
            "Command ID: %s | TelescopeOn completed with result=%s",
            self.component_manager.command_id,
            result_code.name,
        )
        self.update_callback(task_callback, result_code, message)

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
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing TelescopeOn command",
            self.command_id,
        )
        self.component_manager.component.desired_telescope_state = DevState.ON

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOn command"
        )

        unavailable_devices: list = []
        for return_codes, message_or_unique_ids in [
            self.set_standby_fp_mode_dishes(),
            self.turn_on_csp(),
            self.turn_on_sdp(),
            self.turn_on_subarrays(),
        ]:
            resultcode_msg = self.process_resultcode_devices(
                unavailable_devices, return_codes, message_or_unique_ids
            )
            if resultcode_msg[0] == ResultCode.FAILED:
                return resultcode_msg
        return self.return_result(unavailable_devices)

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
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing TelescopeOn command",
            self.command_id,
        )
        self.component_manager.component.desired_telescope_state = DevState.ON

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOn command"
        )
        # send commands to sub-devices
        # import debugpy; debugpy.debug_this_thread()
        unavailable_devices: list = []
        for return_codes, message_or_unique_ids in [
            self.turn_on_mccs(),
            self.turn_on_subarrays(),
            self.turn_on_csp(),
            self.turn_on_sdp(),
        ]:
            # condition for exception raised during invoking command
            resultcode_msg = self.process_resultcode_devices(
                unavailable_devices, return_codes, message_or_unique_ids
            )
            if resultcode_msg[0] == ResultCode.FAILED:
                return resultcode_msg

        return self.return_result(unavailable_devices)

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

    def update_task_status(self, **kwargs):
        """Updates task status implemented to"""

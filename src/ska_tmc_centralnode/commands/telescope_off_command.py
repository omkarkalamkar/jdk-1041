"""Command class for TelescopeOff()"""

import threading
from typing import List, Optional, Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.type_hints import TaskCallbackType
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
            component_manager,
            adapter_factory,
            timeout_subarrays,
            step_sleep,
            logger=logger,
            *args,
            **kwargs,
        )

    def telescope_off(
        self,
        task_callback: TaskCallbackType,
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
        if task_abort_event:
            self.task_abort_event = task_abort_event
        task_callback(status=TaskStatus.IN_PROGRESS)
        return_code, message = self.do(argin=None)
        self.logger.info(
            "Command ID: %s | TelescopeOff completed with result=%s",
            self.component_manager.command_id,
            return_code.name,
        )
        self.update_callback(task_callback, return_code, message)

        return return_code, message

    def do_mid(self, argin=None) -> Tuple[ResultCode, str]:
        """
        Method to invoke Off command on lower level devices.

        Args:
            argin (str): Default is None.

        Returns:
            Tuple(ResultCode, str): tuple containing a return code
            and a string message indicating status.

        """
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing TelescopeOff command",
            self.command_id,
        )
        self.component_manager.component.desired_telescope_state = DevState.OFF

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOff command."
        )

        return_codes, message_or_unique_ids = self.turn_off_subarrays()
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

        returncode_msg = self.wait_for_subarray_empty()
        if returncode_msg[0] == ResultCode.FAILED:
            return returncode_msg

        unavailable_devices: list = []
        for return_codes, message_or_unique_ids in [
            self.turn_off_dishes(),
            self.turn_off_csp(),
            self.turn_off_sdp(),
        ]:
            returncode_msg = self.process_resultcode_devices(
                unavailable_devices, return_codes, message_or_unique_ids
            )
            if returncode_msg[0] == ResultCode.FAILED:
                return returncode_msg

        return self.return_result(unavailable_devices)

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
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing TelescopeOff command",
            self.command_id,
        )
        self.component_manager.component.desired_telescope_state = DevState.OFF

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOff command."
        )
        return_codes, message_or_unique_ids = self.turn_off_subarrays()
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

        resultcode_msg = self.wait_for_subarray_empty()
        if resultcode_msg[0] == ResultCode.FAILED:
            return resultcode_msg

        unavailable_devices: list = []
        for return_codes, message_or_unique_ids in [
            self.turn_off_mccs(),
            self.turn_off_csp(),
            self.turn_off_sdp(),
        ]:
            resultcode_msg = self.process_resultcode_devices(
                unavailable_devices, return_codes, message_or_unique_ids
            )
            if resultcode_msg[0] == ResultCode.FAILED:
                return resultcode_msg

        return self.return_result(unavailable_devices)

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

    def update_task_status(self, **kwargs):
        """Updates task status implemented to"""

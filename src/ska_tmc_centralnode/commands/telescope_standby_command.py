"""Command class for TelescopeStandby command"""

import threading
from typing import Any, List, Optional, Tuple

from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tango_base.type_hints import TaskCallbackType
from tango import DevState

from ska_tmc_centralnode.commands.central_node_command import TelescopeOnOff


class TelescopeStandby(TelescopeOnOff):
    """
    A class for CentralNode's TelescopeStandby() command.
    """

    def telescope_standby(
        self,
        task_callback: TaskCallbackType,
        task_abort_event: Optional[threading.Event] = None,
    ) -> None:
        """
        This is a long running method for TelescopeStandby command,
        it executes do hook,
        invokes TelescopeStandby command on lower level devices.

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
            "Command ID: %s | Executing TelescopeStandby command",
            self.component_manager.command_id,
        )
        result_code, message = self.do(argin=None)
        self.logger.info(
            "Command ID: %s | TelescopeStandby completed with result=%s",
            self.component_manager.command_id,
            result_code.name,
        )
        self.update_callback(task_callback, result_code, message)
        return result_code, message

    def do_mid(self, argin=None) -> Tuple[ResultCode, str]:
        """
        Method to invoke TelescopeStandby command on SubarrayNode, CSP and SDP
        Master Leaf Nodes. Also to invoke StandbyFP and then StandbyLP commands
        on Dish Leaf Nodes.

        Args:
            argin (str): Default is None in case of TelescopeStandby.

        Returns:
            Tuple(List, List): tuple containing a return code
            and a string message indicating status.

        """
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing TelescopeStandbyMid command",
            self.command_id,
        )
        self.component_manager.component.desired_telescope_state = (
            DevState.STANDBY
        )

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeStandby command"
        )
        return_codes, message_or_unique_ids = self.turn_standby_subarrays()
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

        self.logger.debug(
            "Waiting for all subarray devices to reach the EMPTY "
            "observation state."
        )
        resultcode_msg = self.wait_for_subarray_empty()
        if resultcode_msg[0] == ResultCode.FAILED:
            return resultcode_msg

        unavailable_devices: list = []
        for return_codes, message_or_unique_ids in [
            self.turn_off_dishes(),
            self.turn_standby_csp(),
            self.turn_standby_sdp(),
        ]:
            resultcode_msg = self.process_resultcode_devices(
                unavailable_devices, return_codes, message_or_unique_ids
            )
            if resultcode_msg[0] == ResultCode.FAILED:
                return resultcode_msg
        return self.return_result(unavailable_devices)

    def do_low(self, argin=None) -> Tuple[ResultCode, str]:
        """
        Method to invoke Standby command on SubarrayNode and MCCS
        Master Leaf Node.

        Args:
            argin (str): Default None.

        Returns:
            Tuple(ResultCode, str): tuple containing a return code
            and a string message indicating status.

        """
        self.set_command_id(self.__class__.__name__)
        self.logger.debug(
            "Command %s: Executing TelescopeStandbyLow command",
            self.command_id,
        )
        self.component_manager.component.desired_telescope_state = (
            DevState.STANDBY
        )

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeStandby command"
        )
        return_codes, message_or_unique_ids = self.turn_standby_subarrays()
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
            self.turn_standby_mccs(),
            self.turn_standby_csp(),
            self.turn_standby_sdp(),
        ]:
            return_code_msg = self.process_resultcode_devices(
                unavailable_devices, return_codes, message_or_unique_ids
            )
            if return_code_msg[0] == ResultCode.FAILED:
                return return_code_msg
        return self.return_result(unavailable_devices)

    def turn_standby_subarrays(
        self,
    ) -> Tuple[List[ResultCode | Any], List[str | Any]]:
        """
        Turns subarrays to standby

        Returns:
            Tuple(List, List): tuple of list of ResultCodes
            and list of messages.

        """
        self.logger.info(
            "Invoking Standby command on: %s",
            [str(adapter.dev_name) for adapter in self.subarray_adapters],
        )
        return self.send_command(
            self.subarray_adapters,
            f"Error in calling Standby command for {self.subarray_adapters}",
            "Standby",
        )

    def turn_standby_sdp(
        self,
    ) -> Tuple[List[ResultCode | Any], List[str | Any]]:
        """
        Turns sdp to standby

        Returns:
            Tuple(List, List): tuple of list of ResultCodes
            and list of messages.

        """
        self.logger.info(
            "Invoking Standby command on: %s", self.sdp_mln_adapter.dev_name
        )
        if self.component_manager.check_if_sdp_mln_is_available() is True:
            return self.send_command(
                [self.sdp_mln_adapter],
                "Error in calling Standby command for"
                + self.sdp_mln_adapter.dev_name,
                "Standby",
            )
        return (
            [ResultCode.REJECTED],
            [
                self.sdp_mln_adapter.dev_name
                + " is not available to receive Standby command"
            ],
        )

    def turn_standby_csp(
        self,
    ) -> Tuple[List[ResultCode | Any], List[str | Any]]:
        """
        Turns csp to standby

        Returns:
            Tuple(List, List): tuple of list of ResultCodes
            and list of messages.

        """
        self.logger.info(
            "Invoking Standby command on: %s ",
            self.csp_mln_adapter.dev_name,
        )
        if self.component_manager.check_if_csp_mln_is_available() is True:
            return self.send_command(
                [self.csp_mln_adapter],
                "Error in calling Standby command for "
                + self.csp_mln_adapter.dev_name,
                "Standby",
            )
        return (
            [ResultCode.REJECTED],
            [
                f"{self.csp_mln_adapter.dev_name} is not available to receive"
                + " Standby command"
            ],
        )

    def turn_standby_mccs(
        self,
    ) -> Tuple[List[ResultCode | Any], List[str | Any]]:
        """
        Turns MCCS into standby

        Returns:
            Tuple(List, List): tuple of list of ResultCodes
            and list of messages.

        """
        self.logger.info(
            "Invoking Standby command on: %s ", self.mccs_mln_adapter.dev_name
        )
        if self.component_manager.check_if_mccs_mln_is_available() is True:
            return self.send_command(
                [self.mccs_mln_adapter],
                "Error in calling Standby command for"
                + self.mccs_mln_adapter.dev_name,
                "Standby",
            )
        return (
            [ResultCode.REJECTED],
            [
                f"{self.mccs_mln_adapter.dev_name} is not available to receive"
                + " Standby command"
            ],
        )

    def turn_off_dishes(
        self,
    ) -> Tuple[List[ResultCode | Any], List[str | Any]]:
        """
        Turns off the dishes

        Returns:
            Tuple(List, List): tuple of list of ResultCodes
            and list of messages.

        """
        self.logger.info(
            "Invoking Off command on: %s",
            [str(adapter.dev_name) for adapter in self.dish_adapters],
        )
        return self.send_command(
            self.dish_adapters,
            f"Error in calling Off() on Dish Leaf Nodes:{self.dish_adapters}",
            "Off",
        )

    def update_task_status(self, **kwargs):
        """blank method for resolving pylint errors"""

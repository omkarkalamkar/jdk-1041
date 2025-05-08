"""Command class for TelescopeStandby command"""
import threading
import time
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from tango import DevState

from ska_tmc_centralnode.commands.central_node_command import TelescopeOnOff


class TelescopeStandby(TelescopeOnOff):
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
        # pylint:disable=keyword-arg-before-vararg
        super().__init__(
            component_manager, adapter_factory, *args, logger=logger, **kwargs
        )
        self._timeout_subarrays = timeout_subarrays
        self._step_sleep = step_sleep

    def telescope_standby(
        self,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """This is a long running method for TelescopeStandby command,
        it executes do hook,
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
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, message),
                exception=message,
            )
        else:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, message),
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

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeStandby command"
        )
        self.logger.info("Invoking Standby command on the lower level devices")
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
            self.turn_standby_csp(),
            self.turn_standby_sdp(),
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
            self.logger.info(f"Unavailable devices are {unavailable_devices}")
            return (
                ResultCode.OK,
                f"Unavailable devices are {unavailable_devices}",
            )

        return (ResultCode.OK, "Command Completed")

    def do_low(self, argin=None):
        """
        Method to invoke Standby command on SubarrayNode and MCCS
        Master Leaf Node.

        param:
            None

        return:
            A tuple containing a return code and a message

        """
        self.component_manager.component.desired_telescope_state = (
            DevState.STANDBY
        )

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeStandby command"
        )
        self.logger.info("Invoking Standby command on the lower level devices")
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
            self.turn_standby_mccs(),
            self.turn_standby_csp(),
            self.turn_standby_sdp(),
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
            self.logger.info(f"Unavailable devices are {unavailable_devices}")
            return (
                ResultCode.OK,
                f"Unavailable devices are {unavailable_devices}",
            )

        return (ResultCode.OK, "Command Completed")

    def turn_standby_subarrays(self):
        """Turns subarrays to standby"""
        self.logger.info(
            "Invoking Standby command: %s",
            [str(adapter.dev_name) for adapter in self.subarray_adapters],
        )
        return self.send_command(
            self.subarray_adapters,
            f"Error in calling Standby command for {self.subarray_adapters}",
            "Standby",
        )

    def turn_standby_sdp(self):
        """Turns sdp to standby"""
        self.logger.info(
            f"Invoking Standby command on: {self.sdp_mln_adapter.dev_name}"
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

    def turn_standby_csp(self):
        """Turns csp to standby"""
        self.logger.info(
            "Invoking Standby command on: %s Devices",
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

    def turn_standby_mccs(self):
        """Turns MCCS into standby"""
        self.logger.info(
            f"Invoking Standby command on:  {self.mccs_mln_adapter.dev_name}"
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

    def turn_off_dishes(self):
        """Turns off the dishes"""
        self.logger.info(
            "Invoking Off command on: %s",
            [str(adapter.dev_name) for adapter in self.dish_adapters],
        )
        return self.send_command(
            self.dish_adapters,
            f"Error in calling Off() on Dish Leaf Nodes:{self.dish_adapters}",
            "Off",
        )

    def update_task_status(self):
        """blank method for resolving pylint errors"""

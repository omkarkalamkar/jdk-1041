import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from tango import DevState

from ska_tmc_centralnode.commands.abstract_command import TelescopeOnOff


class TelescopeOn(TelescopeOnOff):
    """
    A class for CentralNode's TelescopeOn() command.

    TelescopeOn command on Central node enables the telescope to perform further operations
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
        super().__init__(
            component_manager, adapter_factory, *args, logger=logger, **kwargs
        )

    def telescope_on(
        self,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """This is a long running method for TelescopeOn command, it executes do hook,
        invokes TelescopeOn command on lowe level devices.

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
        Method to invoke On command on Lower level devices.

        param argin:
            None.

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
                elif return_code in [ResultCode.REJECTED]:
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

        return (ResultCode.OK, "")

    def turn_on_sdp(self):
        self.logger.info(
            f"Invoking On command for {self.sdp_mln_adapter.dev_name} devices"
        )
        if self.component_manager.check_if_sdp_mln_is_available() is True:
            return self.send_command(
                [self.sdp_mln_adapter],
                f"Error in calling On command for {self.sdp_mln_adapter.dev_name}",
                "On",
            )
        else:
            return (
                [ResultCode.REJECTED],
                [
                    f"{self.sdp_mln_adapter.dev_name} is not available to receive On command"
                ],
            )

    def turn_on_csp(self):
        self.logger.info(
            f"Invoking On command for {self.csp_mln_adapter.dev_name} devices"
        )
        if self.component_manager.check_if_csp_mln_is_available() is True:
            return self.send_command(
                [self.csp_mln_adapter],
                f"Error in calling On command for {self.csp_mln_adapter.dev_name}",
                "On",
            )
        else:
            return (
                [ResultCode.REJECTED],
                [
                    f"{self.csp_mln_adapter.dev_name} is not available to receive On command"
                ],
            )

    def turn_on_subarrays(self):
        self.logger.info(
            f"Invoking On command for {self.subarray_adapters} devices"
        )

        return self.send_command(
            self.subarray_adapters,
            f"Error in calling On command for {self.subarray_adapters}",
            "On",
        )

    def set_standby_fp_mode_dishes(self):
        return self.send_command(
            self.dish_adapters,
            f"Error in calling SetStandbyFPMode() command on {self.dish_adapters}",
            "SetStandbyFPMode",
        )

    def do_low(self, argin=None):
        """
        Method to invoke On command on Lower level devices.

        param argin:
            None.

        """
        self.component_manager.component.desired_telescope_state = DevState.ON

        return_code, message = self.init_adapters()
        if return_code == ResultCode.FAILED:
            return return_code, message

        self.component_manager.log_state(
            "Device states before executing TelescopeOn command"
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
                elif return_code in [ResultCode.REJECTED]:
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

        return (ResultCode.OK, "")

    def turn_on_mccs(self):
        self.logger.info(
            f"Invoking On command for {self.mccs_mln_adapter.dev_name} devices"
        )
        return self.send_command(
            [self.mccs_mln_adapter],
            f"Error in calling On command for {self.mccs_mln_adapter.dev_name}",
            "On",
        )

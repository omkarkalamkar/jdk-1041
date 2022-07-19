import threading
from typing import Callable, Optional

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus
from tango import DevState

from ska_tmc_centralnode.commands.abstract_command import (
    AbstractTelescopeOnOff,
)


class TelescopeOn(AbstractTelescopeOnOff):
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
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self._timeout_mccs = timeout_mccs
        self._step_sleep = step_sleep
        self.init_adapters()

    def telescope_on(
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
        Method to invoke Telescope On command on Lower level devices.

        param argin:
            None.

        """
        self.component_manager.component.desired_telescope_state = DevState.ON
        print(
            "Component.desired telescope state is::::::",
            self.component_manager.component.desired_telescope_state,
        )
        print("Invoking TelescopeOn command on the lower level devices")
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
            "do_mid for TelescopeOn command on the lower level devices is successful"
        )
        return (ResultCode.OK, "")

    def turn_on_sdp(self):
        print("TelescopeOn for Sdp devices")
        return self.send_command(
            [self.tm_leaf_sdp_master_adapter],
            f"Error in calling On() command for {self.tm_leaf_sdp_master_adapter}",
            "On",
        )

    def turn_on_csp(self):
        print("TelescopeOn for Csp devices")
        return self.send_command(
            [self.tm_leaf_csp_master_adapter],
            f"Error in calling On() command for {self.tm_leaf_csp_master_adapter}",
            "On",
        )

    def turn_on_subarrays(self):
        print("TelescopeOn for tm subarrays devices")
        return self.send_command(
            self.tm_subarray_adapters,
            f"Error in calling On() command for {self.tm_subarray_adapters}",
            "On",
        )

    def set_standby_fp_mode_dishes(self):
        print("TelescopeOn for dish devices")
        return self.send_command(
            self.tm_dish_adapters,
            f"Error in calling SetStandbyFPMode() command for {self.tm_dish_adapters}",
            "SetStandbyFPMode",
        )

    def set_operate_mode_dishes(self):
        print("TelescopeOn for dish devices")
        return self.send_command(
            self.tm_dish_adapters,
            f"Error in calling SetOperateMode() command for {self.tm_dish_adapters}",
            "SetOperateMode",
        )

    def do_low(self, argin=None):
        """
        Method to invoke Telescope On command on Lower level devices.

        param argin:
            None.

        """
        self.component_manager.component.desired_telescope_state = DevState.ON

        # send commands to sub-devices
        # import debugpy; debugpy.debug_this_thread()
        for ret_code, message in [
            self.turn_on_mccs_master(),
            self.turn_on_subarrays(),
        ]:
            if ret_code == ResultCode.FAILED:
                return ret_code, message

        return (ResultCode.OK, "")

    def turn_on_mccs_master(self):
        return self.send_command(
            [self.tm_leaf_mccs_master_adapter],
            f"Error in calling On() command for {self.tm_leaf_mccs_master_adapter}",
            "On",
        )

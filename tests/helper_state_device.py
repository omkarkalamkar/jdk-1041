import logging
import time
from ska_tango_base.base import OpStateModel
from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.base.component_manager import BaseComponentManager
from ska_tango_base.subarray import SubarrayComponentManager
from ska_tango_base.control_model import HealthState, ObsState
from ska_tango_base.subarray import SKASubarray, SubarrayObsStateModel
from tango.server import command, attribute
from ska_tango_base.commands import ResultCode

class EmptyComponentManager(BaseComponentManager):
    def __init__(self, 
                op_state_model,
                logger=None,
                *args, **kwargs):
        self.logger = logger
        super().__init__(op_state_model, *args, **kwargs)


class HelperStateDevice(SKASubarray):
    """A generic device for triggering state changes with a command"""

    class InitCommand(SKASubarray.InitCommand):
        def do(self):
            super().do()
            device = self.target
            device.set_change_event("State", True, False)
            device.set_change_event("healthState", True, False)
            return (ResultCode.OK, "")

    # def init_command_objects(self):
    #     super().init_command_objects()
    #     component_args = (self.component_manager, self.op_state_model, self.logger)
    #     self.register_command_object("TelescopeStandby", self.StandbyCommand(*component_args))
    #     self.register_command_object("TelescopeOff", self.OffCommand(*component_args))
    #     self.register_command_object("TelescopeOn", self.OnCommand(*component_args))

    def create_component_manager(self):
        self.op_state_model = OpStateModel(
            logger=self.logger,
            callback=super()._update_state)
        cm =  EmptyComponentManager(
            self.op_state_model, 
            logger=self.logger
        )
        return cm

    def always_executed_hook(self):
        pass

    def delete_device(self):
        pass

    @command(
        dtype_in="DevState",
        doc_in="state to assign",
    )
    def SetDirectState(self, argin):
        """
        Trigger a DevState change
        """
        # import debugpy; debugpy.debug_this_thread()
        if self.dev_state() != argin:
            self.set_state(argin)
            self.push_change_event("State", self.dev_state())

    @command(
        dtype_in=int,
        doc_in="state to assign",
    )
    def SetDirectHealthState(self, argin):
        """
        Trigger a HealthState change
        """
        # import debugpy; debugpy.debug_this_thread()
        value = HealthState(argin)
        if(self._health_state != value):
            self._health_state = HealthState(argin)
            self.push_change_event("healthState", self._health_state)

    def is_TelescopeOn_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def TelescopeOn(self):
        time.sleep(0.1)
        return [[ResultCode.OK], [""]]

    def is_SetStandbyFPMode_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def SetStandbyFPMode(self):
        # import debugpy; debugpy.debug_this_thread()
        time.sleep(0.1)
        return [[ResultCode.OK], [""]]

    def is_SetOperateMode_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def SetOperateMode(self):
        time.sleep(0.1)
        return [[ResultCode.OK], [""]]

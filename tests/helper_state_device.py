import logging
from ska_tango_base.base import OpStateModel, BaseComponentManager
from ska_tango_base.control_model import HealthState, ObsState
from ska_tango_base.subarray import SKASubarray
from tango.server import command

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
            device.set_change_event("obsState", True, False)   

    def create_component_manager(self):
        self.op_state_model = OpStateModel(
            logger=self.logger,
            callback=super()._update_state)
        cm =  EmptyComponentManager(
            self.op_state_model, logger=self.logger
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

    @command(
        dtype_in=int,
        doc_in="state to assign",
    )
    def SetDirectObsState(self, argin):
        """
        Trigger a HealthState change
        """
        # import debugpy; debugpy.debug_this_thread()
        value = ObsState(argin)
        if(self._obs_state != value):
            self._obs_state = ObsState(argin)
            self.push_change_event("obsState", self._obs_state)

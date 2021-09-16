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
            # device = self.target
            # device.op_state_model.perform_action("init_completed")

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
        dtype_in="str",
        doc_in="action to be performed",
    )
    def TriggerStateChange(self, argin):
        """
        Trigger a state change
        """
        # import debugpy; debugpy.debug_this_thread()
        self.op_state_model.perform_action(argin)
        logging.info("%s", self.op_state_model.op_state)

    @command(
        dtype_in="DevState",
        doc_in="state to assign",
    )
    def SetDirectState(self, argin):
        """
        Trigger a DevState change
        """
        # import debugpy; debugpy.debug_this_thread()
        self.set_state(argin)
        logging.info("%s", self.op_state_model.op_state)

    @command(
        dtype_in=int,
        doc_in="state to assign",
    )
    def SetDirectHealthState(self, argin):
        """
        Trigger a HealthState change
        """
        # import debugpy; debugpy.debug_this_thread()
        self._health_state = HealthState(argin)

    @command(
        dtype_in=int,
        doc_in="state to assign",
    )
    def SetDirectObsState(self, argin):
        """
        Trigger a HealthState change
        """
        # import debugpy; debugpy.debug_this_thread()
        self._obs_state = ObsState(argin)

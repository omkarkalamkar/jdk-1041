import time
from ska_tango_base.base import OpStateModel
from ska_tango_base.subarray import SubarrayComponentManager
from ska_tango_base.subarray import SubarrayObsStateModel
from tests.helper_state_device import HelperStateDevice
from ska_tango_base.commands import ResultCode

class EmptySubArrayComponentManager(SubarrayComponentManager):
    def __init__(self, 
                op_state_model, 
                obs_state_model,
                logger=None,
                *args, **kwargs):
        self.logger = logger
        super().__init__(op_state_model, obs_state_model, *args, **kwargs)
        self._assigned_resources = []

    def assign(self, resources):
        self._assigned_resources = resources
        return (ResultCode.OK, "")

    def release(self, resources):
        """
        Release resources from the component.

        :param resources: resources to be released
        """
        self.logger("%s", resources)
        return (ResultCode.OK, "")

    def release_all(self):
        """Release all resources."""
        self._assigned_resources = []
        time.sleep(1)
        return (ResultCode.OK, "")

    def configure(self, configuration):
        """
        Configure the component.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """
        self.logger("%s", configuration)
        time.sleep(1)
        return (ResultCode.OK, "")

    def deconfigure(self):
        """Deconfigure this component."""
        time.sleep(1)
        return (ResultCode.OK, "")

    def scan(self, args):
        """Start scanning."""
        self.logger("%s", args)
        return (ResultCode.OK, "")

    def end_scan(self):
        """End scanning."""
        time.sleep(1)
        return (ResultCode.OK, "")

    def abort(self):
        """Tell the component to abort whatever it was doing."""
        time.sleep(1)
        return (ResultCode.OK, "")

    def obsreset(self):
        """Reset the component to unconfigured but do not release resources."""
        time.sleep(1)
        return (ResultCode.OK, "")

    def restart(self):
        """Deconfigure and release all resources."""
        time.sleep(1)
        return (ResultCode.OK, "")

    @property
    def assigned_resources(self):
        """
        Return the resources assigned to the component.

        :return: the resources assigned to the component
        :rtype: list of str
        """
        # import debugpy; debugpy.debug_this_thread()
        return self._assigned_resources

    @property
    def configured_capabilities(self):
        """
        Return the configured capabilities of the component.

        :return: list of strings indicating number of configured
            instances of each capability type
        :rtype: list of str
        """
        return set()


class HelperSubArrayDevice(HelperStateDevice):
    """A generic device for triggering state changes with a command"""

    class InitCommand(HelperStateDevice.InitCommand):
        def do(self):
            super().do()
            device = self.target
            device.set_change_event("State", True, False)
            device.set_change_event("healthState", True, False)
            device.set_change_event("obsState", True, False)
            return (ResultCode.OK, "")

    def create_component_manager(self):
        self.op_state_model = OpStateModel(
            logger=self.logger,
            callback=super()._update_state)
        self.obs_state_model = SubarrayObsStateModel(
            logger=self.logger, callback=self._update_obs_state
        )
        cm =  EmptySubArrayComponentManager(
            self.op_state_model, self.obs_state_model,
            logger=self.logger
        )
        return cm

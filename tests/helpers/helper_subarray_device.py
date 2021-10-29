from ska_tango_base.base import OpStateModel
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from ska_tango_base.subarray import (
    SKASubarray,
    SubarrayComponentManager,
    SubarrayObsStateModel,
)
from tango import DevState
from tango.server import command


class EmptySubArrayComponentManager(SubarrayComponentManager):
    def __init__(
        self, op_state_model, obs_state_model, logger=None, *args, **kwargs
    ):
        self.logger = logger
        super().__init__(op_state_model, obs_state_model, *args, **kwargs)
        self._assigned_resources = []

    def assign(self, resources):
        self.logger.info("Resources: %s", resources)
        self._assigned_resources = ["0001"]
        return (ResultCode.OK, "")

    def release(self, resources):
        """
        Release resources from the component.

        :param resources: resources to be released
        """
        return (ResultCode.OK, "")

    def release_all(self):
        """Release all resources."""
        self._assigned_resources = []

        return (ResultCode.OK, "")

    def configure(self, configuration):
        """
        Configure the component.

        :param configuration: the configuration to be configured
        :type configuration: dict
        """
        self.logger("%s", configuration)

        return (ResultCode.OK, "")

    def deconfigure(self):
        """Deconfigure this component."""

        return (ResultCode.OK, "")

    def scan(self, args):
        """Start scanning."""
        self.logger("%s", args)
        return (ResultCode.OK, "")

    def end_scan(self):
        """End scanning."""

        return (ResultCode.OK, "")

    def abort(self):
        """Tell the component to abort whatever it was doing."""

        return (ResultCode.OK, "")

    def obsreset(self):
        """Reset the component to unconfigured but do not release resources."""

        return (ResultCode.OK, "")

    def restart(self):
        """Deconfigure and release all resources."""

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


class HelperSubArrayDevice(SKASubarray):
    """A generic device for triggering state changes with a command"""

    def init_device(self):
        super().init_device()
        self._health_state = HealthState.OK

    class InitCommand(SKASubarray.InitCommand):
        def do(self):
            super().do()
            device = self.target
            device.set_change_event("State", True, False)
            device.set_change_event("healthState", True, False)
            device.set_change_event("obsState", True, False)
            return (ResultCode.OK, "")

    def create_component_manager(self):
        self.op_state_model = OpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        self.obs_state_model = SubarrayObsStateModel(
            logger=self.logger, callback=self._update_obs_state
        )
        cm = EmptySubArrayComponentManager(
            self.op_state_model, self.obs_state_model, logger=self.logger
        )
        return cm

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
        # # pylint: disable=E0203
        value = HealthState(argin)
        if self._health_state != value:
            self._health_state = HealthState(argin)
            self.push_change_event("healthState", self._health_state)

    def is_TelescopeOn_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def TelescopeOn(self):
        if self.dev_state() != DevState.ON:
            self.set_state(DevState.ON)
        return [[ResultCode.OK], [""]]

    def is_TelescopeOff_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def TelescopeOff(self):
        if self.dev_state() != DevState.OFF:
            self.set_state(DevState.OFF)
        return [[ResultCode.OK], [""]]

    def is_TelescopeStandBy_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def TelescopeStandBy(self):
        if self.dev_state() != DevState.STANDBY:
            self.set_state(DevState.STANDBY)
        return [[ResultCode.OK], [""]]

    def is_AssignResources_allowed(self):
        """
        Check if command `AssignResources` is allowed in the current device state.

        :return: ``True`` if the command is allowed
        :rtype: boolean
        """
        return True

    def is_ReleaseAllResources_allowed(self):
        """
        Check if command `ReleaseAllResources` is allowed in the current device state.

        :return: ``True`` if the command is allowed
        :rtype: boolean
        """
        return True

    def is_ReleaseResources_allowed(self):
        """
        Check if command `ReleaseAllResources` is allowed in the current device state.

        :return: ``True`` if the command is allowed
        :rtype: boolean
        """
        return True

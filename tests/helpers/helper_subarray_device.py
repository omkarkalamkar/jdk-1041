# Note: This helper class module is explicitly required for CentralNode. Hence kept it here and not in ska-tmc-common repo.
import logging
import time
from typing import Callable

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState, ObsState
from ska_tango_base.subarray import SKASubarray, SubarrayComponentManager
from tango import DevState
from tango.server import attribute, command


class EmptySubArrayComponentManager(SubarrayComponentManager):
    def __init__(
        self,
        logger: logging.Logger,
        communication_state_callback: Callable,
        component_state_callback: Callable,
        **state
    ):
        self.logger = logger
        super().__init__(
            logger,
            communication_state_callback,
            component_state_callback,
            **state
        )
        self._assigned_resources = []

    def assign(self, resources, task_callback):
        self.logger.info("Resources: %s", resources)
        self.logger.info("task_callback: %s", task_callback)
        self._assigned_resources = ["0001"]
        return (ResultCode.OK, "")

    def release(self, resources):
        """
        Release resources from the component.

        :param resources: resources to be released
        """
        return (ResultCode.OK, "")

    def release_all(self, task_callback):
        """Release all resources."""
        self.logger.info("task_callback: %s", task_callback)
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

    def _update_state(self, state, status=None):
        return super()._update_state(state, status)

    def init_device(self):
        super().init_device()
        self._health_state = HealthState.OK
        self._resources_assigned = []

    class InitCommand(SKASubarray.InitCommand):
        def do(self):
            super().do()
            self._device.set_change_event("State", True, False)
            self._device.set_change_event("healthState", True, False)
            self._device.set_change_event("obsState", True, False)
            self._device.set_change_event("assignedResources", True, False)
            return (ResultCode.OK, "")

    """Device attribute."""
    assignedResources = attribute(
        dtype=("str",),
        max_dim_x=100,
        doc="The list of resources assigned to the subarray.",
    )

    def read_assignedResources(self):
        """
        Read the resources assigned to the device.

        :return: Resources assigned to the device.
        """
        return self._resources_assigned

    def create_component_manager(self):
        cm = EmptySubArrayComponentManager(
            logger=self.logger,
            communication_state_callback=None,
            component_state_callback=None,
        )
        return cm

    def set_state(self, state):
        return super().set_state(state)

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
            time.sleep(0.1)
            self.push_change_event("State", self.dev_state())
            time.sleep(0.1)

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

    @command(
        dtype_in=int,
        doc_in="Set ObsState",
    )
    def SetDirectObsState(self, argin):
        """
        Trigger a ObsState change
        """
        # import debugpy; debugpy.debug_this_thread()
        value = ObsState(argin)
        if self._obs_state != value:
            self._obs_state = value
            self.push_change_event("obsState", self._obs_state)

    def is_On_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def On(self):
        if self.dev_state() != DevState.ON:
            self.set_state(DevState.ON)
            self.push_change_event("State", self.dev_state())
        return [[ResultCode.OK], [""]]

    def is_Off_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def Off(self):
        if self.dev_state() != DevState.OFF:
            self.set_state(DevState.OFF)
            self.push_change_event("State", self.dev_state())
        return [[ResultCode.OK], [""]]

    def is_Standby_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def Standby(self):
        if self.dev_state() != DevState.STANDBY:
            self.set_state(DevState.STANDBY)
            self.push_change_event("State", self.dev_state())
        return [[ResultCode.OK], [""]]

    def is_TelescopeOn_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def TelescopeOn(self):
        if self.dev_state() != DevState.ON:
            self.set_state(DevState.ON)
            self.push_change_event("State", self.dev_state())
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
            self.push_change_event("State", self.dev_state())
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
            self.push_change_event("State", self.dev_state())
        return [[ResultCode.OK], [""]]

    def is_AssignResources_allowed(self):
        """
        Check if command `AssignResources` is allowed in the current device state.

        :return: ``True`` if the command is allowed
        :rtype: boolean
        """
        return True

    @command(
        dtype_in=("str"),
        doc_in="The input string in JSON format consists of receptorIDList.",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def AssignResources(self, argin):
        if self._obs_state != ObsState.IDLE:
            self._obs_state = ObsState.IDLE
            self.push_change_event("obsState", self._obs_state)
        self._resources_assigned = ["0001"]
        self.push_change_event("assignedResources", self._resources_assigned)
        return [[ResultCode.OK], [""]]

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

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def ReleaseAllResources(self):
        if self._obs_state != ObsState.EMPTY:
            self._obs_state = ObsState.EMPTY
            self.push_change_event("obsState", self._obs_state)
        self._resources_assigned = []
        self.push_change_event("assignedResources", self._resources_assigned)
        return [[ResultCode.OK], [""]]

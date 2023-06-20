# Note: This helper class module is explicitly required for CentralNode. Hence kept it here and not in ska-tmc-common repo.
import threading
import time

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)
from tango import AttrWriteType, DevState
from tango.server import attribute, command


class CNHelperSubArrayDevice(HelperSubArrayDevice):
    """A generic device for triggering state changes with a command"""

    def _update_state(self, state, status=None):
        return super()._update_state(state, status)

    def init_device(self):
        super().init_device()
        # self._health_state = HealthState.OK
        self._resources_assigned = []
        self._is_subarray_available = False
        # self._defective = False
        # self.dev_name = self.get_name()

    class InitCommand(HelperSubArrayDevice.InitCommand):
        def do(self):
            super().do()
            # self._device.set_change_event("State", True, False)
            # self._device.set_change_event("healthState", True, False)
            # self._device.set_change_event("obsState", True, False)
            self._device.set_change_event("assignedResources", True, False)
            self._device.set_change_event("isSubarrayAvailable", True, False)
            # self._device.set_change_event(
            #     "longRunningCommandResult", True, False
            # )
            return (ResultCode.OK, "")

    """Device attribute."""
    assignedResources = attribute(
        dtype=("str",),
        max_dim_x=100,
        doc="The list of resources assigned to the subarray.",
    )

    isSubarrayAvailable = attribute(
        dtype="DevBoolean", access=AttrWriteType.READ
    )
    # defective = attribute(dtype=bool, doc="Attribute to set device defective")

    def read_assignedResources(self):
        """
        Read the resources assigned to the device.

        :return: Resources assigned to the device.
        """
        return self._resources_assigned

    def read_isSubarrayAvailable(self) -> bool:
        """Returns subarray availability in boolean format."""
        return self._is_subarray_available

    # def read_defective(self):
    #     """
    #     Read the defective attribute value for device.

    #     :return: bool.
    #     """
    #     return self._defective

    # def create_component_manager(self):
    #     cm = EmptySubArrayComponentManager(
    #         logger=self.logger,
    #         communication_state_callback=None,
    #         component_state_callback=None,
    #     )
    #     return cm

    # def set_state(self, state):
    #     return super().set_state(state)

    @command(
        dtype_in="DevBoolean",
        doc_in="Set subarray's availability",
    )
    def SetisSubarrayAvailable(self, value: bool) -> None:
        """This method sets subarray availability in boolean format."""
        if self._is_subarray_available != value:
            self.logger.info("Setting the subarray availability : %s", value)
            self._is_subarray_available = value
            try:
                self.push_change_event(
                    "isSubarrayAvailable", self._is_subarray_available
                )
            except Exception as e:
                self.logger.exception(f"Error pushing the event. {e}")
            self.logger.info("isSubarrayAvailable event pushed...")

    # @command(
    #     dtype_in="DevState",
    #     doc_in="state to assign",
    # )
    # def SetDirectState(self, argin):
    #     """
    #     Trigger a DevState change
    #     """
    #     # import debugpy; debugpy.debug_this_thread()

    #     if self.dev_state() != argin:
    #         self.set_state(argin)
    #         time.sleep(0.1)
    #         self.push_change_event("State", self.dev_state())
    #         time.sleep(0.1)

    # @command(
    #     dtype_in=bool,
    #     doc_in="Set defective",
    # )
    # def SetDefective(self, argin: bool):
    #     """
    #     Sets the defective value.
    #     """
    #     self._defective = argin

    # @command(
    #     dtype_in=int,
    #     doc_in="state to assign",
    # )
    # def SetDirectHealthState(self, argin):
    #     """
    #     Trigger a HealthState change
    #     """
    #     # import debugpy; debugpy.debug_this_thread()
    #     # # pylint: disable=E0203
    #     value = HealthState(argin)
    #     if self._health_state != value:
    #         self._health_state = HealthState(argin)
    #         self.push_change_event("healthState", self._health_state)

    # @command(
    #     dtype_in=int,
    #     doc_in="Set ObsState",
    # )
    # def SetDirectObsState(self, argin):
    #     """
    #     Trigger a ObsState change
    #     """
    #     # import debugpy; debugpy.debug_this_thread()
    #     value = ObsState(argin)
    #     if self._obs_state != value:
    #         self._obs_state = value
    #         self.push_change_event("obsState", self._obs_state)

    # def is_On_allowed(self):
    #     return True

    # @command(
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="(ReturnType, 'informational message')",
    # )
    # def On(self):
    #     if self.dev_state() != DevState.ON:
    #         self.set_state(DevState.ON)
    #         self.push_change_event("State", self.dev_state())
    #     return [[ResultCode.OK], [""]]

    # def is_Off_allowed(self):
    #     return True

    # @command(
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="(ReturnType, 'informational message')",
    # )
    # def Off(self):
    #     if self.dev_state() != DevState.OFF:
    #         self.set_state(DevState.OFF)
    #         self.push_change_event("State", self.dev_state())
    #     return [[ResultCode.OK], [""]]

    # def is_Standby_allowed(self):
    #     return True

    # @command(
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="(ReturnType, 'informational message')",
    # )
    # def Standby(self):
    #     if self.dev_state() != DevState.STANDBY:
    #         self.set_state(DevState.STANDBY)
    #         self.push_change_event("State", self.dev_state())
    #     return [[ResultCode.OK], [""]]

    # def is_TelescopeOn_allowed(self):
    #     return True

    # @command(
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="(ReturnType, 'informational message')",
    # )
    # def TelescopeOn(self):
    #     if self.dev_state() != DevState.ON:
    #         self.set_state(DevState.ON)
    #         self.push_change_event("State", self.dev_state())
    #     return [[ResultCode.OK], [""]]

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
        if self._defective:
            self._obs_state = ObsState.RESOURCING
            self.push_change_event("obsState", self._obs_state)

            command_result = (
                "1000",
                "Error occured on device",
            )
            thread = threading.Thread(
                target=self.push_result_event, args=[command_result]
            )
            thread.start()

            return [[ResultCode.FAILED], ["Device Defective"]]

        if self._obs_state != ObsState.IDLE:
            self._obs_state = ObsState.IDLE
            self.push_change_event("obsState", self._obs_state)
        self._resources_assigned = ["0001"]
        self.push_change_event("assignedResources", self._resources_assigned)

        command_result = ("1000", str(ResultCode.OK.value))
        thread = threading.Thread(
            target=self.push_result_event, args=[command_result]
        )
        thread.start()

        return [[ResultCode.OK], [""]]

    def push_result_event(self, command_result: tuple):
        """Pushes a longRunningCommandResult event after 2 secs with given result."""
        time.sleep(2)
        self.push_change_event("longRunningCommandResult", command_result)

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

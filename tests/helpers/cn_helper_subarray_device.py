# Note: This helper class module is explicitly required for CentralNode. Hence kept it here and not in ska-tmc-common repo.
import json
import threading
import time
from typing import List, Tuple

from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tmc_common import CommandNotAllowed, FaultType
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
        self._resources_assigned = []
        self._is_subarray_available = False
        self._defective = json.dumps(
            {
                "enabled": False,
                "fault_type": FaultType.FAILED_RESULT,
                "error_message": "Default exception.",
                "result": ResultCode.FAILED,
            }
        )
        self.defective_params = json.loads(self._defective)

    class InitCommand(HelperSubArrayDevice.InitCommand):
        def do(self):
            super().do()
            self._device.set_change_event("assignedResources", True, False)
            self._device.set_change_event("isSubarrayAvailable", True, False)
            self._device.set_change_event(
                "longRunningCommandResult", True, False
            )
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
    defective = attribute(dtype=str, access=AttrWriteType.READ)

    def read_defective(self) -> str:
        """
        Returns defective status of devices as a JSON-encoded string.

        :return: JSON-encoded string representing the defective status of devices
        :rtype: str
        """
        return self._defective

    def read_assignedResources(self):
        """
        Read the resources assigned to the device.

        :return: Resources assigned to the device.
        """
        return self._resources_assigned

    def read_isSubarrayAvailable(self) -> bool:
        """Returns subarray availability in boolean format."""
        return self._is_subarray_available

    def push_obs_state_event(self, obs_state: ObsState) -> None:
        """
        Pushes a change event for the provided observation state.

        Args:
            obs_state (ObsState): The observation state to push.

        Returns:
            None
        """
        self.logger.info("Pushing change event for obsState: %s", obs_state)
        self.push_change_event("obsState", obs_state)

    def induce_fault(
        self,
        command_id: str,
    ) -> Tuple[List[ResultCode], List[str]]:
        """Induces fault into device according to given parameters

        :params:

        command_name: Name of the command for which fault is being induced
        dtype: str
        rtype: Tuple[List[ResultCode], List[str]]
        """
        fault_type = self.defective_params["fault_type"]
        result = self.defective_params["result"]
        fault_message = self.defective_params["error_message"]
        intermediate_state = (
            self.defective_params.get("intermediate_state")
            or ObsState.RESOURCING
        )

        if fault_type == FaultType.FAILED_RESULT:
            return [result], [fault_message]

        if fault_type == FaultType.LONG_RUNNING_EXCEPTION:
            thread = threading.Timer(
                self._delay,
                function=self.push_command_result,
                args=[result, command_id, fault_message],
            )
            thread.start()
            return [ResultCode.QUEUED], [command_id]

        if fault_type == FaultType.STUCK_IN_INTERMEDIATE_STATE:
            self._obs_state = intermediate_state
            self.push_obs_state_event(intermediate_state)
            return [ResultCode.QUEUED], [command_id]

        return [ResultCode.OK], [command_id]

    def push_command_result(
        self, result: ResultCode, command_id: str, exception: str = ""
    ) -> None:
        """Push long running command result event for given command.

        :params:

        result: The result code to be pushed as an event
        dtype: ResultCode

        command: The command name for which the event is being pushed
        dtype: str

        exception: Exception message to be pushed as an event
        dtype: str
        """
        if exception:
            command_result = (command_id, exception)
            self.push_change_event("longRunningCommandResult", command_result)
        command_result = (command_id, json.dumps(result))
        thread = threading.Timer(
            self._delay,
            function=self.push_change_event,
            args=["longRunningCommandResult", command_result],
        )
        thread.start()

    @command(
        dtype_in=str,
        doc_in="Set Defective parameters",
    )
    def SetDefective(self, values: str) -> None:
        """
        Trigger defective change
        :param: values
        :type: str
        """
        input_dict = json.loads(values)
        self.logger.info("Setting defective params to %s", input_dict)
        for key, value in input_dict.items():
            self.defective_params[key] = value

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

    def is_On_allowed(self) -> bool:
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def On(self) -> Tuple[List[ResultCode], List[str]]:
        if self.defective_params["enabled"]:
            return [ResultCode.FAILED], [
                "Device is defective, cannot process command."
            ]
        if self.dev_state() != DevState.ON:
            self.set_state(DevState.ON)
            self.push_change_event("State", self.dev_state())
        return [ResultCode.OK], [""]

    def is_Off_allowed(self) -> bool:
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def Off(self) -> Tuple[List[ResultCode], List[str]]:
        if self.defective_params["enabled"]:
            return [ResultCode.FAILED], [
                "Device is defective, cannot process command."
            ]
        if self.dev_state() != DevState.OFF:
            self.set_state(DevState.OFF)
            self.push_change_event("State", self.dev_state())
        return [ResultCode.OK], [""]

    def is_Standby_allowed(self) -> bool:
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def Standby(self) -> Tuple[List[ResultCode], List[str]]:
        """
        This method invokes Standby command on subarray devices
        :return: ResultCode, message
        :rtype: tuple
        """
        if self.defective_params["enabled"]:
            return [ResultCode.FAILED], [
                "Device is defective, cannot process command."
            ]
        if self.dev_state() != DevState.STANDBY:
            self.set_state(DevState.STANDBY)
            self.push_change_event("State", self.dev_state())
        return [ResultCode.OK], [""]

    def is_AssignResources_allowed(self) -> bool:
        """
        This method checks if the AssignResources command is allowed or not
        """
        if self.defective_params["enabled"]:
            if (
                self.defective_params["fault_type"]
                == FaultType.COMMAND_NOT_ALLOWED
            ):
                raise CommandNotAllowed(self.defective_params["error_message"])
        return True

    @command(
        dtype_in=("str"),
        doc_in="The input string in JSON format consists of receptorIDList.",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def AssignResources(
        self, argin: str = ""
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        This is the method to invoke AssignResources command.
        :return: ResultCode, message
        :rtype: tuple
        """
        command_id = f"{time.time()}_AssignResources"
        if self.defective_params["enabled"]:
            return self.induce_fault(command_id)

        self._obs_state = ObsState.RESOURCING
        self.push_obs_state_event(self._obs_state)
        self._resources_assigned = ["SKA001"]
        self.push_change_event("assignedResources", self._resources_assigned)
        thread = threading.Timer(
            self._delay, self.update_device_obsstate, args=[ObsState.IDLE]
        )
        thread.start()
        self.push_command_result(ResultCode.OK, command_id)
        return [ResultCode.OK], [command_id]

    def push_result_event(self, command_result: tuple):
        """Pushes a longRunningCommandResult event after 2 secs with given result."""
        time.sleep(2)
        self.logger.info(f"Pushing the LRCR event: {command_result}")
        self.push_change_event("longRunningCommandResult", command_result)

    def is_ReleaseAllResources_allowed(self) -> bool:
        """
        This method checks if the ReleaseAllResources command is allowed in
        the current device state.
        :return: ResultCode, message
        :rtype: bool
        """
        if self.defective_params["enabled"]:
            if (
                self.defective_params["fault_type"]
                == FaultType.COMMAND_NOT_ALLOWED
            ):
                raise CommandNotAllowed(self.defective_params["error_message"])
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def ReleaseAllResources(self) -> Tuple[List[ResultCode], List[str]]:
        """
        This is the method to invoke ReleaseAllResources command.
        :return: ResultCode, message
        :rtype: tuple
        """
        command_id = f"{time.time()}_ReleaseAllResources"
        if self.defective_params["enabled"]:
            return self.induce_fault(
                command_id,
            )

        self._obs_state = ObsState.RESOURCING
        self.push_obs_state_event(self._obs_state)
        self._resources_assigned = []
        self.push_change_event("assignedResources", self._resources_assigned)
        thread = threading.Timer(
            self._delay, self.update_device_obsstate, args=[ObsState.EMPTY]
        )
        thread.start()
        self.push_command_result(ResultCode.OK, command_id)
        return [ResultCode.OK], [command_id]

    def is_ReleaseResources_allowed(self):
        """
        Check if command `ReleaseAllResources` is allowed in the current device state.

        :return: ``True`` if the command is allowed
        :rtype: boolean
        """
        return True

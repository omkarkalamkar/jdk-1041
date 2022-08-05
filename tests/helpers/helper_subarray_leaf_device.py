import time

from ska_tango_base.base.base_device import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from tango import DevState
from tango.server import command

from ska_tmc_common.test_helpers.helper_csp_master_device import (
    EmptyComponentManager,
)


class HelperSubarrayLeafDevice(SKABaseDevice):
    """A device exposing commands and attributes of the Subarray Leaf Nodes devices."""

    def init_device(self):
        super().init_device()
        self._health_state = HealthState.OK

    class InitCommand(SKABaseDevice.InitCommand):
        def do(self):
            super().do()
            self._device.set_change_event("State", True, False)
            self._device.set_change_event("healthState", True, False)
            return (ResultCode.OK, "")

    def create_component_manager(self):
        cm = EmptyComponentManager(
            logger=self.logger,
            max_workers=None,
            communication_state_callback=None,
            component_state_callback=None,
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
            time.sleep(0.1)
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
        if self._health_state != value:
            self._health_state = HealthState(argin)
            self.push_change_event("healthState", self._health_state)

    def is_On_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def On(self):
        if self.dev_state() != DevState.ON:
            self.set_state(DevState.ON)
            time.sleep(0.1)
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
            time.sleep(0.1)
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
            time.sleep(0.1)
            self.push_change_event("State", self.dev_state())
        return [[ResultCode.OK], [""]]

    def is_AssignResources_allowed(self):
        return True

    @command(
        dtype_in=("str"),
        doc_in="The input string in JSON format consists of receptorIDList.",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def AssignResources(self, argin):
        self.logger.info("AssignResource completed....")
        return [[ResultCode.OK], [""]]

    def is_Configure_allowed(self):
        return True

    @command(
        dtype_in=("str"),
        doc_in="The input string in JSON format",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def Configure(self, argin):
        self.logger.info("Configure completed....")
        return [[ResultCode.OK], [""]]

    def is_Scan_allowed(self):
        return True

    @command(
        dtype_in=("str"),
        doc_in="The input string in JSON format",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def Scan(self, argin):
        self.logger.info("Scan completed....")
        return [[ResultCode.OK], [""]]

    def is_EndScan_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def EndScan(self):
        self.logger.info("EndScan completed....")
        return [[ResultCode.OK], [""]]

    def is_End_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def End(self):
        self.logger.info("End completed....")
        return [[ResultCode.OK], [""]]

    def is_GoToIdle_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def GoToIdle(self):
        self.logger.info("GoToIdle completed....")
        return [[ResultCode.OK], [""]]

    def is_Abort_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def Abort(self):
        self.logger.info("Abort completed....")
        return [[ResultCode.OK], [""]]

    def is_ObsReset_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def ObsReset(self):
        self.logger.info("ObsReset completed....")
        return [[ResultCode.OK], [""]]

    def is_Restart_allowed(self):
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def Restart(self):
        self.logger.info("Restart completed....")
        return [[ResultCode.OK], [""]]

    def is_ReleaseAllResources_allowed(self):
        self.logger.info("In is_ReleaseAllResources_allowed ....... ")
        return True

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def ReleaseAllResources(self):
        self.logger.info("ReleaseAllResources completed....")
        return [[ResultCode.OK], [""]]

    def is_ReleaseResources_allowed(self):
        self.logger.info("In is_ReleaseResources_allowed ....... ")
        return True

    @command(
        dtype_in=("str"),
        doc_in="The input string in JSON format consists of receptorIDList.",
        dtype_out="DevVarLongStringArray",
        doc_out="(ReturnType, 'informational message')",
    )
    def ReleaseResources(self, argin):
        self.logger.info("ReleaseResources completed....")
        return [[ResultCode.OK], [""]]

"""
StartUpTelescope class for CentralNode.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import time
from concurrent.futures import ThreadPoolExecutor
#Tango imports
import tango
from tango import DevState, DevFailed

# Additional import
from ska.base import SKABaseDevice
from ska.base.commands import BaseCommand
from ska.base.commands import ResultCode
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from ska_tmc_centralnode_mid import const
from ska_tmc_centralnode_mid.device_data import DeviceData
from ska_tmc_centralnode_mid.health_state_aggregator import HealthStateAggregator
from ska_tmc_centralnode_mid.desired_telescope_state import DesiredTelescopeState

# PROTECTED REGION END #    //  CentralNode.additional_import

class StartUpTelescope(BaseCommand):
    """
    A class for CentralNode's StartUpTelescope() command.

    StartUpTelescope command on Central node internally invokes TelescopeOn command on Central node.
    """

    def check_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state

        :return: True if this command is allowed to be run in current device state

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state

        """
        if self.state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            tango.Except.throw_exception(
                f"Command StartUpTelescope is not allowed in current state {self.state_model.op_state}.",
                "Failed to invoke StartUpTelescope command on CentralNode.",
                "CentralNode.StartUpTelescope()",
                tango.ErrSeverity.ERR,
            )
        return True

    def do(self):
        """
        Method to invoke StartUpTelescope command.

        param argin:
            None.

        """
        # device_data = DeviceData.get_instance()
        this_server = TangoServerHelper.get_instance()
        message = "Invoking StartUpTelescope command as part of TelescopeOn Command"
        self.logger.info(message)
        # Call TelescopeOn command to maintain the backword compatibility with OET
        try:
            this_server.device.telescope_on_object()
            message = "telescopeOn command Invoked as part of StartupTelescope on CentralNode"
            self.logger.info(message)
            this_server.write_attr("activityMessage", message, False)
            return (ResultCode.OK, const.STR_STARTUP_CMD_ISSUED)
        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_EXE_STARTUPTELESCOPE_CMD}{dev_failed}"
            self.logger.error(log_msg)
            this_server.write_attr("activityMessage", log_msg, False)
            tango.Except.throw_exception(
                log_msg,
                "Error invoking StartUpTelescope command from TelescopeStandby",
                "SubarrayNode.StartUpTelescope()",
                tango.ErrSeverity.ERR
            )
       
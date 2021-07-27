"""
StandByTelescope class for CentralNode.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import time
from concurrent.futures import ThreadPoolExecutor
import threading
#Tango imports
import tango
from tango import DevState, DevFailed

# Additional import
from ska.base import SKABaseDevice
from ska.base.control_model import ObsState
from ska.base.commands import BaseCommand
from ska.base.commands import ResultCode
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from ska_tmc_centralnode_mid import const
from ska_tmc_centralnode_mid.device_data import DeviceData
from ska_tmc_centralnode_mid.desired_telescope_state import DesiredTelescopeState

# PROTECTED REGION END #    //  CentralNode.additional_import


class StandByTelescope(BaseCommand):
    """
    A class for CentralNode's StandByTelescope() command.

    Sets the CentralNode into OFF state.Invokes command on DishLeaf node, SDPMasterLeaf node,
    CSPMasterLeaf node.
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
                f"Command StandByTelescope is not allowed in current state {self.state_model.op_state}.",
                "Failed to invoke StandByTelescope command on CentralNode.",
                "CentralNode.StandByTelescope()",
                tango.ErrSeverity.ERR,
            )
        return True

    def do(self):
        """
        Method to invoke StandByTelescope command on Lower level devices.

        param:
            None

        return:
            A tuple containing a return code and a string message indicating status.

        rtype:
            (ResultCode, str)

        """
        this_server = TangoServerHelper.get_instance()
        message = "Invoking TelescopeOff command as part of StandbyTelescope Command"
        self.logger.info(message)
        # Call telescopeOff command to maintain the backword compatibility with OET
        try:
            this_server.device.telescopeOff()
            message = "TelescopeOff command Invoked as part of StandbyTelescope command on CentralNode"
            self.logger.info(message)
            this_server.write_attr("activityMessage", message, False)
            return (ResultCode.OK, const.STR_STANDBY_CMD_ISSUED)

        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_EXE_STANDBYTELESCOPE_CMD}{dev_failed}"
            self.logger.error(log_msg)
            this_server.write_attr("activityMessage", log_msg, False)
            tango.Except.throw_exception(
                log_msg,
                "Error invoking StandbyTelescope command from StandbyTelescope",
                "CentralNode.StandbyTelescope()",
                tango.ErrSeverity.ERR
            )
        
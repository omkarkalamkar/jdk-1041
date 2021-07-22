import logging
import tango
from tango import DevState
from ska_tmc_centralnode_mid import const
from ska_tmc_centralnode_mid.device_data import DeviceData
from tmc.common.tango_server_helper import TangoServerHelper

class DesiredTelescopeState:
    def __init__(self):
        self.device_data = DeviceData.get_instance()
        self.this_server = TangoServerHelper.get_instance()
        self.device_data.command_in_progress = self.this_server.read_attr("commandInProgress")

    def update_desired_telescope_state(self):
        """
        Checks whether command_in_progress is same as in desired_telescope_state. And update it in desiredTelescopeState attribute. 
        """
        try:
            if self.device_data.command_in_progress in self.device_data.desired_telescope_state:
                self.this_server.write_attr("desiredTelescopeState", self.device_data.desired_telescope_state[self.device_data.command_in_progress], False)
            else:
                raise Exception
        except Exception as exp:
            log_msg = f"{const.ERR_IN_DESIRED_STATE_ATTR}{exp}"
            tango.Except.throw_exception(
                const.STR_CMD_FAILED,
                log_msg,
                "CentralNode.DesiredTelescopeState",
                tango.ErrSeverity.ERR,
            )
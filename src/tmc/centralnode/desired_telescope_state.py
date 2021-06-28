import logging
import tango
from tango import DevState
from tmc.centralnode.device_data import DeviceData
from tmc.common.tango_server_helper import TangoServerHelper

class DesiredTelescopeState:
    def __init__(self):
        self.device_data = DeviceData.get_instance()
        self.this_server = TangoServerHelper.get_instance()
        self.command_in_progress = self.this_server.read_attr("commandInProgress")

    def desired_telescope_state(self):
        # for command_name in self.device_data.desired_telescope_state.keys():
        if self.command_in_progress in self.device_data.desired_telescope_state:
            self.this_server.write_attr("desiredTelescopeState", self.device_data.desired_telescope_state[self.command_in_progress], False)

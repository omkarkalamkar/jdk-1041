"""
StandByTelescope class for CentralNode.
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
from ska.base.control_model import ObsState
from ska.base.commands import BaseCommand
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from tmc.centralnode import const
from tmc.centralnode.device_data import DeviceData
from tmc.centralnode.desired_telescope_state import DesiredTelescopeState

# PROTECTED REGION END #    //  CentralNode.additional_import


class TelescopeOff(BaseCommand):
    """
    A class for CentralNode's TelescopeOff() command.

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
                f"Command TelescopeOff is not allowed in current state {self.state_model.op_state}.",
                "Failed to invoke TelescopeOff command on CentralNode.",
                "CentralNode.TelescopeOff()",
                tango.ErrSeverity.ERR,
            )
        return True

    def do(self):
        """
        Method to invoke telescopeoff command on Lower level devices.

        param:
            None

        return:
            A tuple containing a return code and a string message indicating status.

        rtype:
            (ResultCode, str)

        """
        device_data = DeviceData.get_instance()
        this_server = TangoServerHelper.get_instance()
        device_data.command_in_progress = "TelescopeOff"
        this_server.write_attr("commandInProgress", device_data.command_in_progress, False)
        desired_telescope_state_obj = DesiredTelescopeState()
        desired_telescope_state_obj.desired_telescope_state()
        self.logger.info(type(self.target))
        # this_server = TangoServerHelper.get_instance()
        csp_master_ln_fqdn = this_server.read_property("CspMasterLeafNodeFQDN")[0]
        sdp_master_ln_fqdn = this_server.read_property("SdpMasterLeafNodeFQDN")[0]
        tm_mid_subarrays = this_server.read_property("TMMidSubarrayNodes")
        try:
            self.telescope_off_subarray(tm_mid_subarrays)
            retry_count = 0
            for val in self.subarray_obs_state:
                while retry_count < 3:
                    if self.subarray_obs_state[val] in [ObsState.EMPTY, ObsState.RESOURCING]:
                        break
                    time.sleep(0.1)
                    retry_count+=1
            self.telescope_off_csp(csp_master_ln_fqdn)                                                               
            self.telescope_off_sdp(sdp_master_ln_fqdn)
            self.telescope_off_dish(device_data._dish_leaf_node_devices)
            this_server.write_attr("activityMessage", const.STR_CMD_TELESCOPE_OFF_DISH, False)
            log_msg = const.STR_TELESCOPE_OFF_CMD_ISSUED
            self.logger.info(log_msg)
            this_server.write_attr("activityMessage", log_msg, False)
            # device_data.desired_telescope_state["TelescopeOff"] = self.state_model.op_state
            # this_server.write_attr("desiredTelescopeState", device_data.desired_telescope_state["TelescopeOff"], False)
            this_server.write_attr("commandInProgress", "", False)

        except Exception as e:
            self.logger.exception(e)


    def telescope_off_csp(self, csp_fqdn):
        """
        Create TangoClient for CspMasterLeaf node and call
        telescopeoff method.

        :return: None
        """
        csp_mln_client = TangoClient(csp_fqdn)
        self.telescope_off_leaf_node(csp_mln_client, const.CMD_TELESCOPE_OFF)

    def telescope_off_sdp(self, sdp_fqdn):
        """
        Create TangoClient for SdpMasterLeaf node and call
        telescopeoff method.

        :return: None
        """
        sdp_mln_client = TangoClient(sdp_fqdn)
        self.telescope_off_leaf_node(sdp_mln_client, const.CMD_TELESCOPE_OFF)

    def telescope_off_dish(self, dish_fqdn):
        """
        Create TangoClient for DishLeaf node node and call
        telescopeoff method.

        :return: None
        """
        total_dishes = len(dish_fqdn)
        dish_ln_thread_status = {}
        with ThreadPoolExecutor(total_dishes) as executor:
            for dish in dish_fqdn:
                dish_ln_client = TangoClient(dish)
                dish_ln_thread_status[dish] = executor.submit(self.telescope_off_dish_leaf_node, dish_ln_client)

        # Wait for result
        while not all(thread_status.done() for thread_status in dish_ln_thread_status.values()):
            pass

    def telescope_off_dish_leaf_node(self, tango_client):
        """
        Invoke SetStandbyFPMode, SetStandbyLPMode and Off commands on Dish leaf nodes.

        :param tango_client: Proxy of corresponding node.

        :return: None

        :raises: Devfailed exception if error occures while  executing On command on Dish leaf node.
        """
        try:
            tango_client.send_command(const.CMD_SET_STANDBYFP_MODE)
            log_msg = "SetStandbyFPMode command invoked successfully on {}".format(
                                                tango_client.get_device_fqdn)
            self.logger.debug(log_msg)
            time.sleep(0.2)
            tango_client.send_command(const.CMD_SET_STANDBYLP_MODE)
            log_msg = "SetStandbyLPMode command invoked successfully on {}".format(
                                                      tango_client.get_device_fqdn)
            self.logger.debug(log_msg)
            tango_client.send_command(const.CMD_TELESCOPE_OFF)
            log_msg = "OFF command invoked successfully on {}".format(tango_client.get_device_fqdn)
            self.logger.debug(log_msg)
            return tango_client.get_device_fqdn

        except DevFailed as dev_failed:
            log_msg = f"{const.STR_TELESCOPE_OFF_EXEC}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(const.STR_TELESCOPE_OFF_EXEC, log_msg,
                                         "CentralNode.TelescopeOff", tango.ErrSeverity.ERR)


    def telescope_off_leaf_node(self, tango_client, cmd_name, param=None):
        """
        Invoke command on leaf nodes.

        :param tango_client: proxy of corresponding leaf node
        :param cmd_name: command name
        :param param: Empty list from cspsmn

        :return: None

        :raises: Devfailed exception if error occures while executing command on leaf nodes.

        """
        try:
            tango_client.send_command(cmd_name, param)
            log_msg = "Command {} invoked successfully on {}".format(
                cmd_name, tango_client.get_device_fqdn
            )
            self.logger.debug(log_msg)

        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_EXE_TELESCOPE_OFF_CMD}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(
                const.STR_TELESCOPE_OFF_EXEC,
                log_msg,
                "CentralNode.TelescopeOff",
                tango.ErrSeverity.ERR,
            )


    def telescope_off_subarray(self, subarray_fqdn_list):
        """
        Create TangoClient for Subarray node and call
        standby method.

        :return: None
        """
        total_subarrays = len(subarray_fqdn_list)
        subarray_thread_status = {}
        self.subarray_obs_state = {}
        with ThreadPoolExecutor(total_subarrays) as executor:
            for subarray_fqdn in subarray_fqdn_list:
                subarray_client = TangoClient(subarray_fqdn)
                self.subarray_obs_state[subarray_fqdn] = subarray_client.get_attribute("obsState").value
                subarray_thread_status[subarray_fqdn] = executor.submit(self.telescope_off_leaf_node,
                                                                        subarray_client, const.CMD_TELESCOPE_OFF)
        # Wait for result
        while not all(thread_status.done() for thread_status in subarray_thread_status.values()):
            pass



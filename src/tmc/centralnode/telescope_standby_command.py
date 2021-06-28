"""
TelescopeStandby class for CentralNode.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import time
from concurrent.futures import ThreadPoolExecutor
#Tango imports
import tango
from tango import DevState, DevFailed

# Additional import
from ska.base.commands import BaseCommand
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from tmc.centralnode import const
from tmc.centralnode.device_data import DeviceData
from tmc.centralnode.desired_telescope_state import DesiredTelescopeState

# PROTECTED REGION END #    //  CentralNode.additional_import


class TelescopeStandby(BaseCommand):
    """
    A class for CentralNode's TelescopeStandby() command.

    Invokes command on DishLeaf node, SDPMasterLeaf node,
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
                f"Command TelescopeStandby is not allowed in current state {self.state_model.op_state}.",
                "Failed to invoke TelescopeStandby command on CentralNode.",
                "CentralNode.TelescopeStandby()",
                tango.ErrSeverity.ERR,
            )
        return True

    def do(self):
        """
        Method to invoke TelescopeStandby command on Lower level devices.

        param:
            None

        return:
            none

        """
        self.logger.info(type(self.target))
        device_data = DeviceData.get_instance()
        this_server = TangoServerHelper.get_instance()
        device_data.command_in_progress = "TelescopeStandby"
        this_server.write_attr("commandInProgress", device_data.command_in_progress, False)
        desired_telescope_state_obj = DesiredTelescopeState()
        desired_telescope_state_obj.desired_telescope_state()
        # this_server = TangoServerHelper.get_instance()
        csp_master_ln_fqdn = this_server.read_property("CspMasterLeafNodeFQDN")[0]
        sdp_master_ln_fqdn = this_server.read_property("SdpMasterLeafNodeFQDN")[0]
        tm_mid_subarrays = this_server.read_property("TMMidSubarrayNodes")
        self.telescope_standby_csp(csp_master_ln_fqdn)                                                               
        self.telescope_standby_sdp(sdp_master_ln_fqdn)
        self.telescope_standby_dish(device_data._dish_leaf_node_devices)
        self.telescope_standby_subarray(tm_mid_subarrays)
        this_server.write_attr("activityMessage", const.STR_CMD_TELESCOPESTANDBY, False)
        log_msg = const.STR_TELESCOPE_STANDBY_ISSUED
        self.logger.info(log_msg)
        this_server.write_attr("activityMessage", log_msg, False)
        # device_data.desired_telescope_state["TelescopeStandby"] = DevState.STANDBY
        # this_server.write_attr("desiredTelescopeState", device_data.desired_telescope_state["TelescopeStandby"], False)
        this_server.write_attr("commandInProgress", "", False)

    def telescope_standby_csp(self, csp_fqdn):
        """
        Create TangoClient for CspMasterLeaf node and call
        standby method.

        :return: None
        """
        csp_mln_client = TangoClient(csp_fqdn)
        self.telescope_standby_leaf_node(csp_mln_client, const.CMD_TELESCOPE_STANDBY)

    def telescope_standby_sdp(self, sdp_fqdn):
        """
        Create TangoClient for SdpMasterLeaf node and call
        standby method.

        :return: None
        """
        sdp_mln_client = TangoClient(sdp_fqdn)
        self.telescope_standby_leaf_node(sdp_mln_client, const.CMD_TELESCOPE_STANDBY)

    def telescope_standby_subarray(self, subarray_fqdn_list):
        """
        Create TangoClient for Subarray node and call
        standby method.

        :return: None
        """
        total_subarrays = len(subarray_fqdn_list)
        subarray_thread_status = {}
        with ThreadPoolExecutor(total_subarrays) as executor:
            for subarray_fqdn in subarray_fqdn_list:
                subarray_client = TangoClient(subarray_fqdn)
                subarray_thread_status[subarray_fqdn] = executor.submit(self.telescope_standby_leaf_node,
                                                                        subarray_client, const.CMD_TELESCOPE_STANDBY)
        # Wait for result
        while not all(thread_status.done() for thread_status in subarray_thread_status.values()):
            pass
    
    def telescope_standby_leaf_node(self, tango_client, cmd_name, param=None):
        """
        Invoke TelescopeStandby command on leaf nodes.

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
            log_msg = f"{const.ERR_EXE_TELESCOPE_STANDBY_CMD}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(
                const.STR_TELESCOPE_STANDBY_EXEC,
                log_msg,
                "CentralNode.TelescopeStandby",
                tango.ErrSeverity.ERR,
            )
    
    def telescope_standby_dish(self, dish_fqdn):
        """
        Create TangoClient for DishLeaf node node and call
        standby method.

        :return: None
        """
        total_dishes = len(dish_fqdn)
        dish_ln_thread_status = {}
        with ThreadPoolExecutor(total_dishes) as executor:
            for dish in dish_fqdn:
                dish_ln_client = TangoClient(dish)
                dish_ln_thread_status[dish] = executor.submit(self.telescope_standby_dish_leaf_node, dish_ln_client)

        # Wait for result
        while not all(thread_status.done() for thread_status in dish_ln_thread_status.values()):
            pass
    
    
    def telescope_standby_dish_leaf_node(self, tango_client):
        """
        Invoke TelescopeStandby command on Dish leaf nodes.

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
            tango_client.send_command(const.CMD_TELESCOPE_STANDBY)
            log_msg = "TelescopeStandby command invoked successfully on {}".format(tango_client.get_device_fqdn)
            self.logger.debug(log_msg)
            return tango_client.get_device_fqdn

        except DevFailed as dev_failed:
            log_msg = f"{const.STR_TELESCOPE_STANDBY_EXEC}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(const.STR_TELESCOPE_STANDBY_EXEC, log_msg,
                                         "CentralNode.TelescopeStandby", tango.ErrSeverity.ERR)
                                    
    
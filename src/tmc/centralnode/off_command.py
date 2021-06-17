"""
Off class for CentralNode.
"""
# Standard Python imports
import time
from concurrent.futures import ThreadPoolExecutor
# Tango imports
import tango
from tango import DevState, DevFailed
# Additional import
from ska.base.commands import BaseCommand
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from tmc.centralnode import const
from tmc.centralnode.device_data import DeviceData

class Off(BaseCommand):
    """
    A class for CentralNode's Off() command.

    Sets the CentralNode into OFF state.Invokes command on DishLeaf node, SDPMasterLeaf node and
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
                f"Command Off is not allowed in current state {self.state_model.op_state}.",
                "Failed to invoke Off command on CentralNode.",
                "CentralNode.Off()",
                tango.ErrSeverity.ERR,
            )
        return True

    def do(self):
        """
        Method to invoke Off command on Lower level devices.

        param:
            None

        return:
            None

        """
        device_data = DeviceData.get_instance()
        this_server = TangoServerHelper.get_instance()
        csp_master_ln_fqdn = this_server.read_property("CspMasterLeafNodeFQDN")[0]
        sdp_master_ln_fqdn = this_server.read_property("SdpMasterLeafNodeFQDN")[0]
        self.off_csp(csp_master_ln_fqdn)                                                               
        self.off_sdp(sdp_master_ln_fqdn)
        self.off_dish(device_data._dish_leaf_node_devices)
        log_msg = const.STR_OFF_CMD_ISSUED
        self.logger.info(log_msg)
        this_server.write_attr("activityMessage", log_msg, False)

    def off_csp(self, csp_fqdn):
        """
        Create TangoClient for CspMasterLeaf node and call
        off method.

        :return: None
        """
        csp_mln_client = TangoClient(csp_fqdn)
        self.off_leaf_node(csp_mln_client, const.CMD_OFF)

    def off_sdp(self, sdp_fqdn):
        """
        Create TangoClient for SdpMasterLeaf node and call
        off method.

        :return: None
        """
        sdp_mln_client = TangoClient(sdp_fqdn)
        self.off_leaf_node(sdp_mln_client, const.CMD_OFF)

    def off_leaf_node(self, tango_client, cmd_name, param=None):
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
            log_msg = f"{const.ERR_EXE_OFF_CMD}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(
                const.STR_OFF_EXEC,
                log_msg,
                "CentralNode.Off()",
                tango.ErrSeverity.ERR,
            )

    def off_dish(self, dish_fqdn):
        """
        Create TangoClient for DishLeaf node node and call
        off method.

        :return: None
        """
        total_dishes = len(dish_fqdn)
        dish_ln_thread_status = {}
        with ThreadPoolExecutor(total_dishes) as executor:
            for dish in dish_fqdn:
                dish_ln_client = TangoClient(dish)
                dish_ln_thread_status[dish] = executor.submit(self.off_dish_leaf_node, dish_ln_client)

        # Wait for result
        while not all(thread_status.done() for thread_status in dish_ln_thread_status.values()):
            pass

    def off_dish_leaf_node(self, tango_client):
        """
        Invoke SetStandbyFPMode, SetStandbyLPMode and Off commands on Dish leaf nodes.

        :param tango_client: Proxy of corresponding node.

        :return: None

        :raises: Devfailed exception if error occures while  executing Off command on Dish leaf node.
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

            tango_client.send_command(const.CMD_OFF)
            log_msg = "OFF command invoked successfully on {}".format(tango_client.get_device_fqdn)
            self.logger.debug(log_msg)
            return tango_client.get_device_fqdn

        except DevFailed as dev_failed:
            log_msg = f"{const.STR_OFF_EXEC}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(const.STR_OFF_EXEC, log_msg,
                                         "CentralNode.Off()", tango.ErrSeverity.ERR)
"""
TelescopeOn class for CentralNode.
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
from ska.base.commands import BaseCommand
from ska.base.commands import ResultCode
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from ska_tmc_centralnode_mid import const
from ska_tmc_centralnode_mid.device_data import DeviceData
from ska_tmc_centralnode_mid.health_state_aggregator import HealthStateAggregator
from ska_tmc_centralnode_mid.desired_telescope_state import DesiredTelescopeState

# PROTECTED REGION END #    //  CentralNode.additional_import

class TelescopeOn(BaseCommand):
    """
    A class for CentralNode's TelescopeOn() command.

    TelescopeOn command on Central node enables the telescope to perform further operations
    and observations. It Invokes On command on lower level devices.

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
                f"Command TelescopeOn is not allowed in current state {self.state_model.op_state}.",
                "Failed to invoke TelescopeOn command on CentralNode.",
                "CentralNode.TelescopeOn()",
                tango.ErrSeverity.ERR,
            )
        return True

    def do(self):
        """
        Method to invoke Telescope On command on Lower level devices.

        param argin:
            None.

        """
        device_data = DeviceData.get_instance()
        this_server = TangoServerHelper.get_instance()
        device_data.command_in_progress = "TelescopeOn"
        this_server.write_attr("commandInProgress", device_data.command_in_progress, False)
        desired_telescope_state_obj = DesiredTelescopeState()
        desired_telescope_state_obj.update_desired_telescope_state()
        self.csp_master_ln_fqdn = this_server.read_property("CspMasterLeafNodeFQDN")[0]
        self.sdp_master_ln_fqdn = this_server.read_property("SdpMasterLeafNodeFQDN")[0]
        self.tm_mid_subarrays = this_server.read_property("TMMidSubarrayNodes")
        try:
            # create thread
            self.logger.info("Starting thread to execute telescope on command.")
            telescope_on_thread = threading.Thread(
                target=self.execute_telescope_on,
            )
            telescope_on_thread.start() 
        except Exception as e:
            self.logger.exception(f"Exception in creating telescope_on thread:{e}")
        self.logger.info("Started thread to execute telescope on command.")
    
    def execute_telescope_on(self):
        # Calling TelescopeOn command asynchronously
        try:
            device_data = DeviceData.get_instance()
            this_server = TangoServerHelper.get_instance()
            self.startup_subarray(self.tm_mid_subarrays)
            self.startup_dish(device_data._dish_leaf_node_devices)
            self.startup_sdp(self.sdp_master_ln_fqdn)
            self.startup_csp(self.csp_master_ln_fqdn)
            self.logger.info("Completed thread to execute telescope on command.")
            this_server.write_attr("commandInProgress", "", False)
        except Exception as e:
            self.logger.error(f"Exception in creating telescope_on thread:{e}")
        
    def startup_csp(self, csp_fqdn):
        """
        Create TangoClient for CspMasterLeaf node and call
        startup method.

        :return: None
        """
        self.logger.info("Invoking telescopeOn command on CspMasterLeafNode")
        csp_mln_client = TangoClient(csp_fqdn)
        self.startup_leaf_node(csp_mln_client)

    def startup_sdp(self, sdp_fqdn):
        """
        Create TangoClient for SdpMasterLeaf node and call
        startup method.

        :return: None
        """
        self.logger.info("Invoking telescopeOn command on SdpMasterLeafNode")
        sdp_mln_client = TangoClient(sdp_fqdn)
        self.startup_leaf_node(sdp_mln_client)

    def startup_dish(self, dish_fqdn):
        """
        Create TangoClient for DishLeaf node and call
        startup method.

        :return: None
        """
        total_dishes = len(dish_fqdn)
        dish_ln_thread_status = {}
        self.logger.info("Invoking telescopeOn command on DishLeafNode")
        with ThreadPoolExecutor(total_dishes) as executor:
            for dish in dish_fqdn:
                dish_ln_client = TangoClient(dish)
                dish_ln_thread_status[dish] = executor.submit(self.startup_dish_leaf_node, dish_ln_client)

        # Wait for result
        # while not all(thread_status.done() for thread_status in dish_ln_thread_status.values()):
        #     pass

    def startup_subarray(self, subarray_fqdn_list):
        """
        Create TangoClient for Subarray node and call
        startup method.

        :return: None
        """
        total_subarrays = len(subarray_fqdn_list)
        subarray_thread_status = {}
        self.logger.info("Invoking telescopeOn command on SubarrayNode")
        with ThreadPoolExecutor(total_subarrays) as executor:
            for subarray_fqdn in subarray_fqdn_list:
                subarray_client = TangoClient(subarray_fqdn)
                subarray_thread_status[subarray_fqdn] = executor.submit(self.startup_leaf_node,
                                                              subarray_client)
        # Wait for result
        # while not all(thread_status.done() for thread_status in subarray_thread_status.values()):
        #     pass

    def telescopeon_cmd_ended_cb(self, event):
        """
        Callback function immediately executed when the asynchronous invoked
        command returns.

        :param event: a CmdDoneEvent object. This class is used to pass data
            to the callback method in asynchronous callback model for command
            execution.

        :type: CmdDoneEvent object
            It has the following members:
                - device     : (DeviceProxy) The DeviceProxy object on which the call was executed.
                - cmd_name   : (str) The command name
                - argout_raw : (DeviceData) The command argout
                - argout     : The command argout
                - err        : (bool) A boolean flag set to true if the command failed. False otherwise
                - errors     : (sequence<DevError>) The error stack
                - ext

        :return: none
        """
        # Update logs and activity message attribute with received event
        this_server = TangoServerHelper.get_instance()
        if event.err:
            log_msg = f"{const.ERR_INVOKING_CMD}{event.cmd_name}\n{event.errors}"
            self.logger.error(log_msg)
            this_server.write_attr("activityMessage", log_msg, False)
        else:
            log_msg = f"{const.STR_COMMAND}{event.cmd_name}{const.STR_INVOKE_SUCCESS}"
            self.logger.info(log_msg)
            this_server.write_attr("activityMessage", log_msg, False)

    def startup_leaf_node(self, tango_client, param=None):
        """
        Invoke Telescope On command on leaf nodes.

        :param tango_client: Proxy of corresponding node.

        :return: None

        :raises: Devfailed exception if error occures while  executing On command on leaf node.
        """
        try:
            tango_client.send_command_async(const.CMD_TELESCOPE_ON, param, self.telescopeon_cmd_ended_cb)
            log_msg = "Telescope On command invoked successfully on {}".format(
                tango_client.get_device_fqdn()
            )
            self.logger.debug(log_msg)

        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_EXE_ON_CMD}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(
                const.STR_ON_EXEC,
                log_msg,
                "CentralNode.TelescopeOnCommand",
                tango.ErrSeverity.ERR,
            )

    def startup_dish_leaf_node(self, tango_client, param=None):
        """
        Invoke Telescope On, SetStandbyFPMode and SetOperateMode commands on Dish leaf nodes.

        :param tango_client: Proxy of corresponding node.

        :return: None

        :raises: Devfailed exception if error occures while  executing Telescope On command on Dish leaf node.
        """
        try:
            tango_client.send_command(const.CMD_SET_STANDBYFP_MODE)
            log_msg = "SetStandbyFPMode command invoked successfully on {}".format(
                tango_client.get_device_fqdn()
            )
            self.logger.debug(log_msg)
            time.sleep(0.2)
            tango_client.send_command_async(const.CMD_SET_OPERATE_MODE, param, self.telescopeon_cmd_ended_cb)
            log_msg = "SetOperateMode command invoked successfully on {}".format(
                tango_client.get_device_fqdn()
            )
            self.logger.debug(log_msg)

        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_EXE_ON_CMD}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(
                const.STR_ON_EXEC,
                log_msg,
                "CentralNode.TelescopeOnCommand",
                tango.ErrSeverity.ERR,
            )

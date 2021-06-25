"""
TelescopeOn class for CentralNode.
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
from tmc.centralnode import const
from tmc.centralnode.device_data import DeviceData
from tmc.centralnode.health_state_aggregator import HealthStateAggregator

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
        self.logger.info(type(self.target))
        this_server = TangoServerHelper.get_instance()
        csp_master_ln_fqdn = this_server.read_property("CspMasterLeafNodeFQDN")[0]
        sdp_master_ln_fqdn = this_server.read_property("SdpMasterLeafNodeFQDN")[0]
        tm_mid_subarrays = this_server.read_property("TMMidSubarrayNodes")
        self.startup_sdp(sdp_master_ln_fqdn)
        self.startup_dish(device_data._dish_leaf_node_devices)
        this_server.write_attr("activityMessage", const.STR_CMD_TELESCOPEON, False)
        self.startup_csp(csp_master_ln_fqdn)
        self.startup_subarray(tm_mid_subarrays)
        log_msg = const.STR_ON_CMD_ISSUED
        self.logger.info(log_msg)
        this_server.write_attr("activityMessage", const.STR_ON_CMD_ISSUED, False)
        device_data.desired_telescope_state["TelescopeON"] = self.state_model.op_state
        # device_data.desired_telescope_state["TelescopeON"] = DevState.ON
        this_server.write_attr("desiredTelescopeState", device_data.desired_telescope_state["TelescopeON"], False)

    def startup_csp(self, csp_fqdn):
        """
        Create TangoClient for CspMasterLeaf node and call
        startup method.

        :return: None
        """
        csp_mln_client = TangoClient(csp_fqdn)
        self.startup_leaf_node(csp_mln_client)

    def startup_sdp(self, sdp_fqdn):
        """
        Create TangoClient for SdpMasterLeaf node and call
        startup method.

        :return: None
        """
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
        with ThreadPoolExecutor(total_dishes) as executor:
            for dish in dish_fqdn:
                dish_ln_client = TangoClient(dish)
                dish_ln_thread_status[dish] = executor.submit(self.startup_dish_leaf_node, dish_ln_client)

        # Wait for result
        while not all(thread_status.done() for thread_status in dish_ln_thread_status.values()):
            pass

    def startup_subarray(self, subarray_fqdn_list):
        """
        Create TangoClient for Subarray node and call
        startup method.

        :return: None
        """
        total_subarrays = len(subarray_fqdn_list)
        subarray_thread_status = {}
        with ThreadPoolExecutor(total_subarrays) as executor:
            for subarray_fqdn in subarray_fqdn_list:
                subarray_client = TangoClient(subarray_fqdn)
                subarray_thread_status[subarray_fqdn] = executor.submit(self.startup_leaf_node,
                                                              subarray_client)
        # Wait for result
        while not all(thread_status.done() for thread_status in subarray_thread_status.values()):
            pass

    def startup_leaf_node(self, tango_client):
        """
        Invoke Telescope On command on leaf nodes.

        :param tango_client: Proxy of corresponding node.

        :return: None

        :raises: Devfailed exception if error occures while  executing On command on leaf node.
        """
        try:
            tango_client.send_command(const.CMD_TELESCOPE_ON)
            log_msg = "Telescope On command invoked successfully on {}".format(
                tango_client.get_device_fqdn
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

    def startup_dish_leaf_node(self, tango_client):
        """
        Invoke Telescope On, SetStandbyFPMode and SetOperateMode commands on Dish leaf nodes.

        :param tango_client: Proxy of corresponding node.

        :return: None

        :raises: Devfailed exception if error occures while  executing Telescope On command on Dish leaf node.
        """
        try:
            tango_client.send_command(const.CMD_TELESCOPE_ON)
            log_msg = "Telescope On command invoked successfully on {}".format(
                tango_client.get_device_fqdn
            )
            self.logger.debug(log_msg)
            tango_client.send_command(const.CMD_SET_STANDBYFP_MODE)
            log_msg = "SetStandbyFPMode command invoked successfully on {}".format(
                tango_client.get_device_fqdn
            )
            self.logger.debug(log_msg)
            time.sleep(0.2)
            tango_client.send_command(const.CMD_SET_OPERATE_MODE)
            log_msg = "SetOperateMode command invoked successfully on {}".format(
                tango_client.get_device_fqdn
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

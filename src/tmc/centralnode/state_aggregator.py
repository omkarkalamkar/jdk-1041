"""
state_aggregator class for CentralNode.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import logging

# Tango imports
import tango
from tango import DevFailed

# Additional import
from ska.base.control_model import HealthState
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from tmc.centralnode import const
from tmc.centralnode.device_data import DeviceData
# PROTECTED REGION END #    //  CentralNode.additional_import


class StateAggregator(Aggregator):
    """
    Aggregator class for state event subscription and state
    callback.
    """
    
    def __init__(self, logger=None):
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.device_data = DeviceData.get_instance()
        self.subarray_state_map = {}
        self.csp_subarray_state_map = {}
        self.sdp_subarray_state_map = {}
        self.dish_state_map = {}

        self.this_server = TangoServerHelper.get_instance()
        # FQDN are passed as string here. Once tangoserverhelper is updated in tmccommonpackage, then this will be updated.
        self.csp_master_ln_fqdn = ""
        self.sdp_master_ln_fqdn = ""
        self.dln_prefix = ""
        self.tm_mid_subarrays = []
        self.tm_mid_csp_subarrays_leaf_nodes = []
        self.tm_mid_sdp_subarrays_leaf_nodes = []

        self.csp_master_ln_fqdn = self.this_server.read_property("CspMasterLeafNodeFQDN")[0]
        self.sdp_master_ln_fqdn = self.this_server.read_property("SdpMasterLeafNodeFQDN")[0]
        self.dln_prefix = self.this_server.read_property("DishLeafNodePrefix")[0]
        self.num_dishes = self.this_server.read_property("NumDishes")
        self.tm_mid_subarrays = self.this_server.read_property("TMMidSubarrayNodes")
        self.tm_mid_csp_subarrays_leaf_nodes = self.this_server.read_property("TMMidCspSubarrayLeafNodeFQDN")
        self.tm_mid_sdp_subarrays_leaf_nodes = self.this_server.read_property("TMMidSdpSubarrayLeafNodeFQDN")

        self.state_event_map = {}


    def subscribe_event(self):
        """
        Method for event subscription. Calls separate subscribe event methods for CSPMasterLeafNode, SDPMasterLeafNode, 
        TM Subarray, DishLeafNode, CSPSubarrayLeafNode, SDPSubarrayLeafNode state attribute subscription.
        """
        self.csp_master_ln_state_subscribe_event()
        self.sdp_master_ln_state_subscribe_event()
        self.subarray_state_subscribe_event()
        self.dish_ln_state_subscribe_event()
        self.csp_sa_ln_state_subscribe_event()
        self.sdp_sa_ln_state_subscribe_event()


    def csp_master_ln_state_subscribe_event(self):
        """
        Method to subscribe to state change event on CSPMasterLeafNode.

        :raises: Devfailed exception if error occurs while subscribing event.
        """
        try:
            csp_master_ln_client = TangoClient(self.csp_master_ln_fqdn)
            self.csp_mln_event_id = csp_master_ln_client.subscribe_attribute(
                const.EVT_SUBSR_STATE, self.state_cb
            )
            self.state_event_map[csp_master_ln_client] = self.csp_mln_event_id
        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_SUBSR_CSP_MASTER_LN_STATE}{dev_failed}"
            self.logger.exception(dev_failed)
            self.this_server.write_attr("activityMessage", const.ERR_SUBSR_CSP_MASTER_LN_STATE, False)
            tango.Except.throw_exception(
                const.STR_CMD_FAILED,
                log_msg,
                "CentralNode.StateSubscribeEvent",
                tango.ErrSeverity.ERR,
            )

    def sdp_master_ln_state_subscribe_event(self):
        """
        Method to subscribe to state change event on SdpMasterLeafNode.

        :raises: Devfailed exception if error occurs while subscribing event.
        """
        try:
            sdp_master_ln_client = TangoClient(self.sdp_master_ln_fqdn)
            self.sdp_mln_event_id = sdp_master_ln_client.subscribe_attribute(
                const.EVT_SUBSR_STATE, self.state_cb
            )
            self.state_event_map[sdp_master_ln_client] = self.sdp_mln_event_id
        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_SUBSR_SDP_MASTER_LN_STATE}{dev_failed}"
            self.logger.exception(dev_failed)
            self.this_server.write_attr("activityMessage", const.ERR_SUBSR_SDP_MASTER_LN_STATE, False)
            tango.Except.throw_exception(
                const.STR_CMD_FAILED,
                log_msg,
                "CentralNode.StateSubscribeEvent",
                tango.ErrSeverity.ERR,
            )

    def subarray_state_subscribe_event(self):
        """
        Method to subscribe to state change event on SubarrayNode.

        :raises: Devfailed exception if erroe occurs while subscribing event.
        """
        self.tm_mid_subarrays = self.this_server.read_property("TMMidSubarrayNodes")
        for subarray_fqdn in self.tm_mid_subarrays:
            subarray_client = TangoClient(subarray_fqdn)
            # updating the subarray_state_map with device name (as ska_mid/tm_subarray_node/1) and its value which is required in callback
            self.subarray_state_map[subarray_fqdn] = -1
            try:
                sa_event_id = subarray_client.subscribe_attribute(
                    const.EVT_SUBSR_STATE, self.state_cb
                )
                self.state_event_map[subarray_client] = sa_event_id
            except DevFailed as dev_failed:
                log_msg = f"{const.ERR_SUBSR_SA_STATE}{dev_failed}"
                self.logger.exception(dev_failed)
                self.this_server.write_attr("activityMessage", const.ERR_SUBSR_SA_STATE, False)
                tango.Except.throw_exception(
                    const.STR_CMD_FAILED,
                    log_msg,
                    "CentralNode.StateSubscribeEvent",
                    tango.ErrSeverity.ERR,
                )

    def dish_ln_state_subscribe_event(self):
        """
        Method to subscribe to state change event on DishLeafNode.

        :raises: Devfailed exception if error occurs while subscribing event.
        """
        for dish in range(1, (self.num_dishes + 1)):
            dish_ln_fqdn = self.dln_prefix + f"000{dish}"
            dish_ln_client = TangoClient(dish_ln_fqdn)
            self.dish_state_map[dish_ln_fqdn] = -1
            try:
                self.dish_ln_event_id = dish_ln_client.subscribe_attribute(
                    const.EVT_SUBSR_STATE, self.state_cb
                )
                self.state_event_map[dish_ln_client] = self.dish_ln_event_id
            except DevFailed as dev_failed:
                log_msg = f"{const.ERR_SUBSR_DISH_LN_STATE}{dev_failed}"
                self.logger.exception(dev_failed)
                self.this_server.write_attr("activityMessage", const.ERR_SUBSR_DISH_LN_STATE, False)
                tango.Except.throw_exception(
                    const.STR_CMD_FAILED,
                    log_msg,
                    "CentralNode.StateSubscribeEvent",
                    tango.ErrSeverity.ERR,
                )

    def csp_sa_ln_state_subscribe_event(self):
        """
        Method to subscribe to state change event on CspSubarrayLeafNode.

        :raises: Devfailed exception if error occurs while subscribing event.
        """
        for csp_sa_ln_fqdn in self.tm_mid_csp_subarrays_leaf_nodes:
            csp_sa_ln_client = TangoClient(csp_sa_ln_fqdn)
            self.csp_subarray_state_map[csp_sa_ln_fqdn] = -1
            try:
                csp_sa_event_id = csp_sa_ln_client.subscribe_attribute(
                    const.EVT_SUBSR_STATE, self.state_cb
                )
                self.state_event_map[csp_sa_ln_client] = csp_sa_event_id
            except DevFailed as dev_failed:
                log_msg = f"{const.ERR_SUBSR_CSP_SA_LN_STATE}{dev_failed}"
                self.logger.exception(dev_failed)
                self.this_server.write_attr("activityMessage", const.ERR_SUBSR_CSP_SA_LN_STATE, False)
                tango.Except.throw_exception(
                    const.STR_CMD_FAILED,
                    log_msg,
                    "CentralNode.StateSubscribeEvent",
                    tango.ErrSeverity.ERR,
                )

    def sdp_sa_ln_state_subscribe_event(self):
        """
        Method to subscribe to health state change event on SdpSubarrayLeafNode.

        :raises: Devfailed exception if error occurs while subscribing event.
        """
        for sdp_sa_ln_fqdn in self.tm_mid_csp_subarrays_leaf_nodes:
            sdp_sa_ln_client = TangoClient(sdp_sa_ln_fqdn)
            self.sdp_subarray_state_map[sdp_sa_ln_fqdn] = -1
            try:
                sdp_sa_event_id = sdp_sa_ln_client.subscribe_attribute(
                    const.EVT_SUBSR_STATE, self.state_cb
                )
                self.state_event_map[sdp_sa_ln_client] = sdp_sa_event_id
            except DevFailed as dev_failed:
                log_msg = f"{const.ERR_SUBSR_SDP_SA_LN_STATE}{dev_failed}"
                self.logger.exception(dev_failed)
                self.this_server.write_attr("activityMessage", const.ERR_SUBSR_SDP_SA_LN_STATE, False)
                tango.Except.throw_exception(
                    const.STR_CMD_FAILED,
                    log_msg,
                    "CentralNode.StateSubscribeEvent",
                    tango.ErrSeverity.ERR,
                )

    def unsubscribe_event(self):
        """
        Method to unsubscribe to health state change event on CspMasterLeafNode, SdpMasterLeafNode and SubarrayNode
        """
        for tango_client in self.state_event_map:
            log_message = "Unsubscribing ObsState of: {}".format(
                tango_client.get_device_fqdn
            )
            self.logger.debug(log_message)
            tango_client.unsubscribe_attribute(
                self.state_event_map[tango_client]
            )
        self.state_event_map.clear()


    def state_cb(self, event):
        """
        Retrieves the subscribed Subarray health state, aggregates them to calculate the
        telescope health state.

        :param event: A TANGO_CHANGE event on Subarray healthState.

        :return: None
        """
        device_data = DeviceData.get_instance()
        log_msg = f'Health state attribute change event is : {event.attr_name}'
        self.logger.info(log_msg)
        log_msg = f'Health state attribute change event is: {event.attr_value.value}'
        self.logger.info(log_msg)
        
        def _update_health_state(self, fqdn_device_health_state_map: dict):
            health_state = event.attr_value.value
            attr_name = event.attr_name
            self.logger.info(f"Health state is: {health_state}")
            for fqdn, dd_health_state in fqdn_device_health_state_map.items():
                if fqdn in attr_name:
                    setattr(device_data, dd_health_state, health_state)
                    if "subarray" in fqdn:
                        self.subarray_state_map[attr_name] = health_state
                    elif "csp" in fqdn:
                        self.logger.info(f"Health state msg in CSP Master: {attr_name}")
                        self.logger.info(f"CSP Master health is: {health_state}")
                    break
            else:
                self.logger.debug(const.EVT_UNKNOWN)
                # TODO: update read_activity message for unknown events

        def _generate_health_state_log_msg(self, health_state):
            health_state_string_map = {
                HealthState.OK: const.STR_OK,
                HealthState.DEGRADED: const.STR_DEGRADED,
                HealthState.FAILED: const.STR_FAILED,
                HealthState.UNKNOWN: const.STR_UNKNOWN
            }
            log_msg = f"{const.STR_HEALTH_STATE}{event.device}{health_state_string_map[health_state]}"                       
            self.logger.info(log_msg)
          
        def _calculate_health_state(health_states):
            unique_states = set(health_states)
            if unique_states == set([HealthState.OK]):
                self.this_server.device.attr_map["telescopeHealthState"] = HealthState.OK
                _generate_health_state_log_msg(self, HealthState.OK)
            elif HealthState.FAILED in unique_states:
                self.this_server.device.attr_map["telescopeHealthState"] = HealthState.FAILED
                _generate_health_state_log_msg(self, HealthState.FAILED)
            elif HealthState.DEGRADED in unique_states:
                self.this_server.device.attr_map["telescopeHealthState"] = HealthState.DEGRADED
                _generate_health_state_log_msg(self, HealthState.DEGRADED)
            else:
                self.this_server.device.attr_map["telescopeHealthState"] = HealthState.UNKNOWN
                _generate_health_state_log_msg(self, HealthState.UNKNOWN)
            
        if not event.err:
            fqdn_device_health_state_map = {
                const.PROP_DEF_VAL_TM_MID_SA1: "_subarray1_health_state",
                const.PROP_DEF_VAL_TM_MID_SA2: "._subarray2_health_state",
                const.PROP_DEF_VAL_TM_MID_SA3: "_subarray3_health_state",
                self.csp_master_ln_fqdn: "_csp_master_health",
                self.sdp_master_ln_fqdn: "_sdp_master_health"
            }
            _update_health_state(self, fqdn_device_health_state_map)

            health_states = [
                device_data._csp_master_health,
                device_data._sdp_master_health
            ]
            health_states = health_states + list(self.subarray_state_map.values())
            _calculate_health_state(health_states)

        else:
            # TODO: For future reference
            self.this_server.write_attr("activityMessage", f"{const.ERR_SUBSR_SA_STATE}{event}", False)
            self.logger.info(f"{const.ERR_SUBSR_SA_STATE}{event}")
            self.logger.critical(f"{const.ERR_SUBSR_SA_STATE}{event}")

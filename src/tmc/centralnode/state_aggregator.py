"""
state_aggregator class for CentralNode.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import logging
import threading

# Tango imports
import tango
from tango import DevFailed, DevState

# Additional import
from ska.base.control_model import HealthState
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from tmc.centralnode import const
from tmc.centralnode.device_data import DeviceData
from tmc.centralnode.aggregator import Aggregator
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
        self.state_event_map = {}
        self.this_server = TangoServerHelper.get_instance()
        self.csp_master_ln_fqdn = ""
        self.sdp_master_ln_fqdn = ""
        self.dln_prefix = ""
        self.tm_mid_subarrays = []
        self.tm_mid_csp_subarrays_leaf_nodes = []
        # create lock
        self.state_callback_lock = threading.Lock()
        self.tm_mid_sdp_subarrays_leaf_nodes = []
        # Read the property of devices
        self.csp_master_ln_fqdn = self.this_server.read_property("CspMasterLeafNodeFQDN")[0]
        self.sdp_master_ln_fqdn = self.this_server.read_property("SdpMasterLeafNodeFQDN")[0]
        self.dln_prefix = self.this_server.read_property("DishLeafNodePrefix")[0]
        self.num_dishes = self.this_server.read_property("NumDishes")[0]
        self.tm_mid_subarrays = self.this_server.read_property("TMMidSubarrayNodes")
        self.tm_mid_csp_subarrays_leaf_nodes = self.this_server.read_property("TMMidCspSubarrayLeafNodes")
        self.tm_mid_sdp_subarrays_leaf_nodes = self.this_server.read_property("TMMidSdpSubarrayLeafNodes")


    def subscribe_event(self):  ###when this method will call?????
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
        for dish in range(0, len(self.num_dishes)):
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
        for sdp_sa_ln_fqdn in self.tm_mid_sdp_subarrays_leaf_nodes:
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
        Method to unsubscribe to state change event on CspMasterLeafNode, SdpMasterLeafNode,  CspSubarrayLeafNode, SdpSubarrayLeafNode, DishLeafNode and SubarrayNode
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
        Retrieves the subscribed state for CspMasterLeafNode, SdpMasterLeafNode, CspSubarrayLeafNode, SdpSubarrayLeafNode, DishLeafNode 
        and Subarray, aggregates them to calculate the CentralNode state.

        :param event: A TANGO_CHANGE event on CspMasterLeafNode, SdpMasterLeafNode, CspSubarrayLeafNode, SdpSubarrayLeafNode, DishLeafNode 
        and Subarray healthState.

        :return: None
        """
        device_data = DeviceData.get_instance()
        # Lock for thread 1
        self.state_callback_lock.acquire()
        log_msg = f'State attribute change event is : {event.attr_name}'
        self.logger.info(log_msg)
        log_msg = f'State attribute change event is: {event.attr_value.value}'
        self.logger.info(log_msg)
        
        def _update_state(self, fqdn_device_state_map: dict):
            device_state = event.attr_value.value
            attr_name = event.attr_name
            self.logger.info(f"State is: {device_state}")
            try:
                for fqdn, dd_device_state in fqdn_device_state_map.items():
                    if fqdn in attr_name:
                        #setattr(device_data, dd_device_state, device_state)
                        if "tm_subarray" in fqdn:
                            self.subarray_state_map[attr_name] = device_state
                            print("::::::::::subarray state map is::::::::::::::", self.subarray_state_map[attr_name])
                        elif "csp_subarray" in fqdn:
                            self.csp_subarray_state_map[attr_name] = device_state
                            print("::::::::::csp subarray state map is::::::::::::::", self.csp_subarray_state_map[attr_name])
                        elif "sdp_subarray" in fqdn:
                            self.sdp_subarray_state_map[attr_name] = device_state
                            print("::::::::::sdp subarray state map is::::::::::::::", self.sdp_subarray_state_map[attr_name])
                        elif "ska_mid/tm_leaf_node/d" in fqdn:
                            self.dish_state_map[attr_name] = device_state
                            print("::::::::::dish state map is::::::::::::::", self.dish_state_map[attr_name])
                        elif "csp_master" in fqdn:
                            device_data._csp_master_state = device_state
                            self.logger.info(f"State msg in CSP Master: {attr_name}")
                            self.logger.info(f"CSP Master state is: {device_state}")
                        elif "sdp_master" in fqdn:
                            device_data._sdp_master_state = device_state
                            self.logger.info(f"State msg in SDP Master: {attr_name}")
                            self.logger.info(f"SDP Master state is: {device_state}")
                        else:
                            print("Condition is not statisfied")
                        break
                else:
                    self.logger.debug(const.EVT_UNKNOWN)
                    # TODO: update read_activity message for unknown events
            except Exception as e:
                print("::::::Exception is:::::", str(e))

        if not event.err:
            fqdn_device_state_map = {
                const.PROP_DEF_VAL_TM_MID_SA1: "_subarray1_state",
                const.PROP_DEF_VAL_TM_MID_SA2: "_subarray2_state",
                const.PROP_DEF_VAL_TM_MID_SA3: "_subarray3_state",
                const.PROP_DEF_VAL_TM_MID_CSPSA_LN1: "_csp_subarray1_ln_state",
                const.PROP_DEF_VAL_TM_MID_CSPSA_LN2: "_csp_subarray2_ln_state",
                const.PROP_DEF_VAL_TM_MID_CSPSA_LN3: "_csp_subarray3_ln_state",
                const.PROP_DEF_VAL_TM_MID_SDPSA_LN1: "_sdp_subarray1_ln_state",
                const.PROP_DEF_VAL_TM_MID_SDPSA_LN2: "_sdp_subarray2_ln_state",
                const.PROP_DEF_VAL_TM_MID_SDPSA_LN3: "_sdp_subarray3_ln_state",
                const.PROP_DEF_VAL_TM_MID_DLN1: "_dish_ln1_state", 
                const.PROP_DEF_VAL_TM_MID_DLN2: "_dish_ln2_state",
                const.PROP_DEF_VAL_TM_MID_DLN3: "_dish_ln3_state",
                const.PROP_DEF_VAL_TM_MID_DLN4: "_dish_ln4_state",
                const.PROP_DEF_VAL_TM_MID_CSPM_LN: "_csp_master_state",
                const.PROP_DEF_VAL_TM_MID_SDPM_LN: "_sdp_master_state"
            }
            _update_state(self, fqdn_device_state_map)

            device_data.tmc_device_states = [
                device_data._csp_master_state,
                device_data._sdp_master_state
            ]
            device_data.tmc_device_states = device_data.tmc_device_states + list(self.subarray_state_map.values()) + list(self.csp_subarray_state_map.values()) + list(self.sdp_subarray_state_map.values()) + list(self.dish_state_map.values()) 

            device_data._attr_callback_trigger.set()  # start state calculation 
            self.state_callback_lock.release()  # release the lock                             
        else:
            # TODO: For future reference
            self.this_server.write_attr("activityMessage", f"{const.ERR_SUBSR_SA_STATE}{event}", False)
            self.logger.info(f"{const.ERR_SUBSR_SA_STATE}{event}")
            self.logger.critical(f"{const.ERR_SUBSR_SA_STATE}{event}")
        

    def start_state_aggregation(self):
        # Create event for state change
        self._state_event = threading.Event() # thread control
        # create thread
        self.logger.info("Starting thread to calculate state for Tmc devices.")
        self.state_calculator_thread = threading.Thread(
            target=self.calculate_state,
        )
        self.state_calculator_thread.start()


    def stop_state_aggregation(self):   ## when to call this method ????     
        # Stop thread of state calculation
        self.logger.info("Stopping state calculator thread.")
        self._state_event.set()
        self.state_calculator_thread.join()
        self.logger.info("State calculator thread stopped.")


    def generate_state_log_msg(self, device_state):
        state_string_map = {
            DevState.ON: const.STR_ON,
            DevState.OFF: const.STR_OFF,
            DevState.INIT: const.STR_INIT,
            DevState.FAULT: const.STR_FAULT
        }
        log_msg = f"{const.STR_STATE}{state_string_map[device_state]}"                       
        self.logger.info(log_msg)
        

    def calculate_state(self):
        device_data = DeviceData.get_instance()
        print("::::::::self._attr_callback_trigger.isSet():::::::", device_data._attr_callback_trigger.isSet())
        print("::::::::self._state_event.isSet():::::::", self._state_event.isSet())
        while not self._state_event.isSet():
            if device_data._attr_callback_trigger.isSet():
                print("::::::::::::Inside if block since attr is triggered:::::::::::")
                #calculation logic
                print("*******tmc_device_states in if block before set()******", device_data.tmc_device_states)
                unique_states = set(device_data.tmc_device_states)
                print("::::::::::::::::::::::unique_states::::::::::::::::::", unique_states)
                if unique_states == set([DevState.ON]):
                    print("Inside if for DevState.ON")
                    self.this_server.device._op_state = DevState.ON 
                    print("self.this_server.device._op_state is", self.this_server.device._op_state)
                    #print("state of CN is",str(self.this_server.device.get_state()))
                    self.generate_state_log_msg(DevState.ON)
                    print("Device is ON")
                elif unique_states == set([DevState.OFF]):
                    self.this_server.device._op_state = DevState.OFF
                    self.generate_state_log_msg(DevState.ON)
                    print("Device is OFF")
                elif DevState.INIT in unique_states:
                    self.this_server.device._op_state = DevState.INIT
                    self.generate_state_log_msg(DevState.INIT)
                    print("Device is INIT")
                elif DevState.FAULT in unique_states:
                    self.this_server.device._op_state = DevState.FAULT
                    self.generate_state_log_msg(DevState.FAULT)
                    print("Device is FAULT")
                else:
                    self.logger.info("State can not be state")
                device_data._attr_callback_trigger.clear()

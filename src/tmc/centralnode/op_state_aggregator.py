"""
state_aggregator class for CentralNode.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import logging
import threading
import time

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


class OpStateAggregator(Aggregator):
    """
    Aggregator class for state event subscription and state
    callback.
    """

    def __init__(self, logger=None):
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        try:
            self.device_data = DeviceData.get_instance()
            self.subarray_state_map = {}
            self.csp_subarray_state_map = {}
            self.sdp_subarray_state_map = {}
            self.dish_state_map = {}
            self.state_event_map = {}
            self.this_server = TangoServerHelper.get_instance()
            self.tm_mid_subarrays = []
            self.tm_mid_csp_subarrays_leaf_nodes = []
            # create lock
            self.state_callback_lock = threading.Lock()
            self.tm_mid_sdp_subarrays_leaf_nodes = []
            # Read the property of devices
            self.csp_master_ln_fqdn = self.this_server.read_property(
                "CspMasterLeafNodeFQDN"
            )[0]
            self.sdp_master_ln_fqdn = self.this_server.read_property(
                "SdpMasterLeafNodeFQDN"
            )[0]
            self.dln_prefix = self.this_server.read_property("DishLeafNodePrefix")[0]
            self.num_dishes = self.this_server.read_property("NumDishes")[0]
            self.tm_mid_subarrays = self.this_server.read_property("TMMidSubarrayNodes")
            self.tm_mid_csp_subarrays_leaf_nodes = self.this_server.read_property(
                "TMMidCspSubarrayLeafNodes"
            )
            self.tm_mid_sdp_subarrays_leaf_nodes = self.this_server.read_property(
                "TMMidSdpSubarrayLeafNodes"
            )
            self.fqdn_device_state_list = [self.sdp_master_ln_fqdn, self.csp_master_ln_fqdn, self.dln_prefix]
            self.fqdn_device_state_list = self.fqdn_device_state_list + list(self.tm_mid_subarrays) + list(self.tm_mid_csp_subarrays_leaf_nodes) + list(self.tm_mid_sdp_subarrays_leaf_nodes)
            self.logger.info(f"fqdn_device_state_list is: {self.fqdn_device_state_list}")

        except Exception as exe:
            self.logger.exception(exe)

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
            self.state_event_map[csp_master_ln_client] = csp_master_ln_client.subscribe_attribute(
                const.EVT_SUBSR_STATE, self.state_callback
            )
        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_SUBSR_CSP_MASTER_LN_STATE}{dev_failed}"
            self.logger.exception(dev_failed)
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
            self.state_event_map[sdp_master_ln_client] = sdp_master_ln_client.subscribe_attribute(
                const.EVT_SUBSR_STATE, self.state_callback
            )
        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_SUBSR_SDP_MASTER_LN_STATE}{dev_failed}"
            self.logger.exception(dev_failed)
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
        for subarray_fqdn in self.tm_mid_subarrays:
            subarray_client = TangoClient(subarray_fqdn)
            try:
                self.state_event_map[subarray_client] = subarray_client.subscribe_attribute(
                    const.EVT_SUBSR_STATE, self.state_callback
                )
            except DevFailed as dev_failed:
                log_msg = f"{const.ERR_SUBSR_SA_STATE}{dev_failed}"
                self.logger.exception(dev_failed)
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
        dish_device_ids = [str(i).zfill(4) for i in range(1, 5)]
        for dish in range(0, len(dish_device_ids)):
            dish_ln_fqdn = self.dln_prefix + dish_device_ids[dish]
            dish_ln_client = TangoClient(dish_ln_fqdn)
            try:
                self.state_event_map[dish_ln_client] = dish_ln_client.subscribe_attribute(
                    const.EVT_SUBSR_STATE, self.state_callback
                )
            except DevFailed as dev_failed:
                log_msg = f"{const.ERR_SUBSR_DISH_LN_STATE}{dev_failed}"
                self.logger.exception(dev_failed)
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
            try:
                self.state_event_map[csp_sa_ln_client] = csp_sa_ln_client.subscribe_attribute(
                    const.EVT_SUBSR_STATE, self.state_callback
                )
            except DevFailed as dev_failed:
                log_msg = f"{const.ERR_SUBSR_CSP_SA_LN_STATE}{dev_failed}"
                self.logger.exception(dev_failed)
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
            try:
                self.state_event_map[sdp_sa_ln_client] = sdp_sa_ln_client.subscribe_attribute(
                    const.EVT_SUBSR_STATE, self.state_callback
                )
            except DevFailed as dev_failed:
                log_msg = f"{const.ERR_SUBSR_SDP_SA_LN_STATE}{dev_failed}"
                self.logger.exception(dev_failed)
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
            tango_client.unsubscribe_attribute(self.state_event_map[tango_client])
        self.state_event_map.clear()

    def state_callback(self, event):
        """
        Retrieves the subscribed state for CspMasterLeafNode, SdpMasterLeafNode, CspSubarrayLeafNode, SdpSubarrayLeafNode, DishLeafNode
        and SubarrayNode

        :param event: A TANGO_CHANGE event on CspMasterLeafNode, SdpMasterLeafNode, CspSubarrayLeafNode, SdpSubarrayLeafNode, DishLeafNode
        and Subarray State.

        :return: None
        """
        try:
            device_data = DeviceData.get_instance()
            # Lock for thread 1
            self.state_callback_lock.acquire()
            log_msg = f"State attribute change event is : {event.attr_name}"
            self.logger.debug(log_msg)
            if event.attr_value:
                log_msg = f"State attribute change event is: {event.attr_value.value}"
                self.logger.debug(log_msg)

                if not event.err:
                    self.update_state(event, self.fqdn_device_state_list)
                    device_data.tmc_device_states = [
                        device_data._csp_master_state,
                        device_data._sdp_master_state,
                    ]
                    device_data.tmc_device_states = (
                        device_data.tmc_device_states
                        + list(self.subarray_state_map.values())
                        + list(self.csp_subarray_state_map.values())
                        + list(self.sdp_subarray_state_map.values())
                        + list(self.dish_state_map.values())
                    )
                    self.logger.info(
                                f"tmc_device_states in state_callback is:{device_data.tmc_device_states}"
                            )
                    device_data._state_callback_trigger.set()  # start state calculation
                    self.state_callback_lock.release() # release the lock
                    # while True:
                    #     if not device_data._state_callback_trigger.isSet():
                    #         self.state_callback_lock.release() # release the lock
                    #     time.sleep(0.1)
                else:
                    # TODO: For future reference
                    self.logger.info(f"{const.ERR_SUBSR_SA_STATE}{event}")
        except Exception as e:
            self.logger.exception(f"In state_callback exception is:{e}")


    def update_state(self, event, fqdn_device_state_list: dict):
        device_data = DeviceData.get_instance()
        device_state = event.attr_value.value
        attr_name = event.attr_name
        self.logger.info(
            f"Change event received for atttribute:{attr_name} with value : {device_state}"
                        )
        try:
            for fqdn in fqdn_device_state_list:
                if fqdn in attr_name:
                    if "tm_subarray" in fqdn:
                        self.subarray_state_map[attr_name] = device_state
                        self.logger.info(
                            f"Subarray state map is:{self.subarray_state_map[attr_name]}"
                        )
                    elif "csp_subarray" in fqdn:
                        self.csp_subarray_state_map[attr_name] = device_state
                        self.logger.info(
                            f"Csp subarray state map is:{self.csp_subarray_state_map[attr_name]}"
                        )
                    elif "sdp_subarray" in fqdn:
                        self.sdp_subarray_state_map[attr_name] = device_state
                        self.logger.info(
                            f"sdp subarray state map is:{self.sdp_subarray_state_map[attr_name]}"
                        )
                    elif "ska_mid/tm_leaf_node/d" in fqdn:
                        self.dish_state_map[attr_name] = device_state
                        self.logger.info(
                            f"dish state map is is:{self.dish_state_map[attr_name]}"
                        )
                    elif "csp_master" in fqdn:
                        device_data._csp_master_state = device_state
                        self.logger.info(f"State msg in CSP Master: {attr_name}")
                        self.logger.info(f"CSP Master state is: {device_state}")
                    elif "sdp_master" in fqdn:
                        device_data._sdp_master_state = device_state
                        self.logger.info(f"State msg in SDP Master: {attr_name}")
                        self.logger.info(f"SDP Master state is: {device_state}")
                    else:
                        self.logger.info(f"Condition is not statisfied")
                    break
            else:
                self.logger.debug(const.EVT_UNKNOWN)
        except Exception as e:
            self.logger.exception(f"In update_state exception is:{e}")

    def start_state_aggregation(self):
        try:
            # Create event for state change
            self._state_event = threading.Event()  # thread control
            # create thread
            self.logger.info("Starting thread to calculate state for Tmc devices.")
            self.state_calculator_thread = threading.Thread(
                target=self.calculate_state,
            )
            self.state_calculator_thread.start()
        except Exception as e:
            self.logger.exception(f"In start_state_aggregation exception is:{e}")

    def stop_state_aggregation(self):  ## when to call this method ????
        # Stop thread of state calculation
        self.logger.info("Stopping state calculator thread.")
        self._state_event.set()
        self.state_calculator_thread.join()
        self.logger.info("State calculator thread stopped.")

    def generate_state_log_msg(self, device_state):
        try:
            state_string_map = {
                DevState.ON: const.STR_ON,
                DevState.OFF: const.STR_OFF,
                DevState.INIT: const.STR_INIT,
                DevState.FAULT: const.STR_FAULT,
            }
            # Need to work on getting device name here
            log_msg = f"{const.STR_STATE}{state_string_map[device_state]}"
            self.logger.info(log_msg)
        except Exception as e:
            self.logger.exception(f"In generate_state_log_msg exception is:{e}")

    def calculate_state(self):
        try:
            device_data = DeviceData.get_instance()
            while not self._state_event.isSet():
                if device_data._state_callback_trigger.isSet():
                    # calculation logic
                    unique_states = set(device_data.tmc_device_states)
                    self.logger.info(
                                f"tmc_device_states is:{device_data.tmc_device_states}"
                            )
                    self.logger.info(
                        f"unique_states is:{unique_states}"
                    )
                    if unique_states == set([DevState.ON]):
                        self.this_server.set_state(DevState.ON)
                        self.generate_state_log_msg(self.this_server.get_state())
                    elif unique_states == set([DevState.OFF]):
                        #Set trigger to call CentralNode On command
                        device_data._tmc_off_trigger.set()
                        self.generate_state_log_msg(self.this_server.get_state())
                    elif DevState.INIT in unique_states:
                        self.this_server.set_state(DevState.INIT)
                        self.generate_state_log_msg(self.this_server.get_state())
                    elif DevState.FAULT in unique_states:
                        self.this_server.set_state(DevState.FAULT)
                        self.generate_state_log_msg(self.this_server.get_state())
                    else:
                        self.this_server.set_state(DevState.UNKNOWN)
                        self.logger.info(
                                f"tmc_device_states is:{device_data.tmc_device_states}"
                            )
                        self.logger.info(
                            f"unique_states is:{unique_states}"
                        )
                        self.logger.info("State can not be set")
                    device_data._state_callback_trigger.clear()
                    #self.state_callback_lock.release() # release the lock
        except Exception as e:
            self.logger.exception(f"In calculate_state exception is:{e}")

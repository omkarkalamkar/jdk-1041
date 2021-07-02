"""
telescope_state_aggregator class for CentralNode.
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


class TelescopeStateAggregator(Aggregator):
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
            self.csp_master_state_map = {}
            self.telescope_state_event_map = {}
            self.this_server = TangoServerHelper.get_instance()
            self.telescope_state_callback_lock = threading.Lock()
    
            self.csp_master_fqdn = self.this_server.read_property(
                "CspMasterFQDN"
            )[0]

            self.fqdn_device_telescope_state_list = [self.csp_master_fqdn]
            self.logger.info(f"fqdn_device_telescope_state_list is: {self.fqdn_device_telescope_state_list}")

        except Exception as exe:
            self.logger.exception(exe)

    def subscribe_event(self):
        """
        Method for event subscription. Calls separate subscribe event methods for CSP Master Node, SDP Master Node,
        Dish Master state attribute subscription.
        """
        self.csp_master_state_subscribe_event()


    def csp_master_state_subscribe_event(self):
        """
        Method to subscribe to state change event on CSP Master Node.

        :raises: Devfailed exception if error occurs while subscribing event.
        """
        try:
            csp_master_client = TangoClient(self.csp_master_fqdn)
            self.csp_master_state_map[self.csp_master_fqdn] = -1
            self.telescope_state_event_map[csp_master_client] = csp_master_client.subscribe_attribute(
                const.EVT_SUBSR_STATE, self.telescope_state_callback
            )
        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_SUBSR_CSP_MASTER_STATE}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(
                const.STR_CMD_FAILED,
                log_msg,
                "CentralNode.StateSubscribeEvent",
                tango.ErrSeverity.ERR,
            )


    def unsubscribe_event(self):
        """
        Method to unsubscribe to state change event on Csp Master Node, Sdp Master Node, Dish Master.
        """
        

        for tango_client in self.telescope_state_event_map:
            log_message = "Unsubscribing ObsState of: {}".format(
                tango_client.get_device_fqdn
            )
            self.logger.debug(log_message)
            tango_client.unsubscribe_attribute(self.telescope_state_event_map[tango_client])
        self.telescope_state_event_map.clear()

    def telescope_state_callback(self, event):
        """
        Retrieves the subscribed state for Csp Master Node, Sdp Master Node, Dish Master.

        :param event: A TANGO_CHANGE event on Csp Master Node, Sdp Master Node, Dish Master.

        :return: None
        """
        
        device_data = DeviceData.get_instance()
        # Lock for thread 1
        self.telescope_state_callback_lock.acquire()
        log_msg = f"State attribute change event is : {event.attr_name}"
        self.logger.debug(log_msg)
        log_msg = f"State attribute change event is: {event.attr_value.value}"
        self.logger.debug(log_msg)

        if not event.err:
            self.update_telescope_state(event, self.fqdn_device_telescope_state_list)
            # device_data.telescope_device_states = [
            #     device_data._csp_master_state,
            # ]
            device_data.telescope_device_states = (
                device_data.telescope_device_states
                + list(self.csp_master_state_map.values())
            )

            device_data._attr_callback_trigger.set()  # start state calculation
            self.telescope_state_callback_lock.release()  # release the lock
        else:
            # TODO: For future reference
            self.logger.info(f"{const.ERR_SUBSR_TELESCOPE_STATE}{event}")


    def update_telescope_state(self, event, fqdn_device_telescope_state_list: dict):
        device_data = DeviceData.get_instance()
        device_state = event.attr_value.value
        attr_name = event.attr_name
        self.logger.info(f"State is: {device_state}")
        try:
            for fqdn in fqdn_device_telescope_state_list:
                if fqdn in attr_name:
                    if "mid_csp/elt/master" in fqdn:
                        self.csp_master_state_map[attr_name] = device_state
                        self.logger.info(
                            f"Subarray state map is:{self.csp_master_state_map[attr_name]}"
                        )
            else:
                self.logger.debug(const.EVT_UNKNOWN)
        except Exception as e:
            self.logger.exception(e)

    def start_telescope_state_aggregation(self):
        # Create event for telescope state change

        self._telescope_state_event = threading.Event()  # thread control
        # create thread
        self.logger.info("Starting thread to calculate telescope state for Tmc devices.")
        self.telescope_state_calculator_thread = threading.Thread(
            target=self.calculate_telescope_state,
        )
        self.telescope_state_calculator_thread.start()

    def stop_telescope_state_aggregation(self): 
        # Stop thread of telescope state calculation

        self.logger.info("Stopping telescope state calculator thread.")
        self._telescope_state_event.set()
        self.telescope_state_calculator_thread.join()
        self.logger.info("Telescope State calculator thread stopped.")

    def generate_state_log_msg(self, device_state):
        state_string_map = {
            DevState.ON: const.STR_ON,
            DevState.OFF: const.STR_OFF,
            DevState.INIT: const.STR_INIT,
            DevState.FAULT: const.STR_FAULT,
            DevState.STANDBY: const.STR_STANDBY,
        }
        log_msg = f"{const.STR_STATE}{state_string_map[device_state]}"
        self.logger.info(log_msg)

    def calculate_telescope_state(self):
        device_data = DeviceData.get_instance()
        while not self._telescope_state_event.isSet():
            if device_data._attr_callback_trigger.isSet():
                # calculation logic
                unique_telescope_states = set(device_data.telescope_device_states)
                if unique_telescope_states == set([DevState.ON]):
                    self.this_server.set_state(DevState.ON)
                    self.generate_state_log_msg(DevState.ON)
                elif unique_telescope_states == set([DevState.OFF]):
                    self.this_server.set_state(DevState.OFF)
                    self.generate_state_log_msg(DevState.OFF)
                elif DevState.INIT in unique_telescope_states:
                    self.this_server.set_state(DevState.INIT)
                    self.generate_state_log_msg(DevState.INIT)
                elif DevState.FAULT in unique_telescope_states:
                    self.this_server.set_state(DevState.FAULT)
                    self.generate_state_log_msg(DevState.FAULT)
                elif DevState.STANDBY in unique_telescope_states:
                    self.this_server.set_state(DevState.STANDBY)
                    self.generate_state_log_msg(DevState.STANDBY)

                else:
                    self.this_server.set_state(DevState.UNKNOWN)
                    self.logger.info("State can not be state")
                device_data._attr_callback_trigger.clear()

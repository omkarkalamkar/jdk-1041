"""
This module provided a reference implementation of a BaseComponentManager.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import threading
import time
from tango import DevState
from ska_tango_base.base import BaseComponentManager
from ska_tango_base.control_model import HealthState
from ska_tmc_centralnode_mid.model.component import Component, DeviceInfo, SubArrayDeviceInfo
from ska_tmc_centralnode_mid.manager.monitoring_loop import MonitoringLoop
from ska_tmc_centralnode_mid.manager.event_receiver import EventReceiver
from ska_tmc_centralnode_mid.manager.adapters import BaseAdapter, AdapterType, CspMaster, Dish
from ska_tmc_centralnode_mid.dev_factory import DevFactory

from ska_tmc_centralnode_mid.model.input import InputParameter

class CNComponentManager(BaseComponentManager):
    """
    A component manager for The Central Node component.

    It supports:

    * Monitoring its component, e.g. detect that it has been turned off
      or on
    
    * Fetching the latest SCM indicator values of the components periodically 
      and trigger the TMC and telescope state aggregation
    
    * Receiving the change events from the component and trigger 
      the TMC and telescope state aggregation
    """

    def __init__(self, 
        op_state_model, 
        logger=None, 
        _component=None,
        _update_device_callback = None,
        _update_telescope_state_callback = None,
        _update_telescope_health_state_callback = None,
        _update_tmc_op_state_callback = None,
        _update_subarray_health_state_callback = None,
        _monitoring_loop = True,
        _event_receiver = True,
        *args, **kwargs):
        """
        Initialise a new ComponentManager instance.

        :param op_state_model: the op state model used by this component
            manager
        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        """
        self.logger = logger

        self._component = _component or Component(logger)
        
        if _monitoring_loop:
            self._monitoring_loop = MonitoringLoop(self, logger)

        if _event_receiver:
            self._event_receiver = EventReceiver(self, logger)

        self._component.set_op_callbacks(_update_device_callback, 
                                         _update_telescope_state_callback, 
                                         _update_telescope_health_state_callback, 
                                         _update_tmc_op_state_callback,
                                         _update_subarray_health_state_callback
                                         )

        super().__init__(op_state_model, *args, **kwargs)

        if _monitoring_loop:
            self._monitoring_loop.start()

        if _event_receiver:
            self._event_receiver.start()

        # self._adapters = []
        
        self._input_parameter = InputParameter(None)

        self._command_executed = []

        # self._dev_factory = DevFactory()

    # def input_parameter_callback(self):
    #     # change the corresponding adapeter!
    #     for dev_name in self._input_parameter.tm_subarray_dev_names:
            
    #     self._input_parameter.csp_subarray_dev_names = ("3", "4")
    #     self._input_parameter.tm_dish_dev_names = ("5")
    #     self._input_parameter.sdp_subarray_dev_names = ("6")
    #     self._input_parameter.csp_master_dev_name = "7"
    #     self._input_parameter.sdp_master_dev_name = "8"
    #     self._input_parameter.tm_leaf_sdp_master_dev_name = "9"
    #     self._input_parameter.tm_leaf_csp_master_dev_name = "10"

    # @property
    # def adapters(self):
    #     """
    #     Return the list of the adapters used

    #     :return: list of adapters
    #     :rtype BaseAdapter
    #     """
    #     return self._adapters

    # def add_adapter(self, adapter):
    #     """
    #     Add an adapter at the list of adpters
    #     if not present

    #     :param adapter: adapter object
    #     :type adapter: BaseAdapter
    #     """
    #     if adapter not in self.adapters:
    #         self._adapters.append(adapter)

    # def get_or_create_adapter(self, dev_name, adapter_type = AdapterType.BASE):
    #     """
    #     Get or create a generic adapter 

    #     :param dev_name: device name
    #     :type str
    #     """
    #     for adapter in self.adapters:
    #         if adapter.dev_name == dev_name:
    #             return adapter

    #     if adapter_type ==  AdapterType.DISH:
    #         return Dish(dev_name, self._dev_factory.get_device(dev_name))
    #     elif adapter_type == AdapterType.CSP:
    #         return CspMaster(dev_name, self._dev_factory.get_device(dev_name))
    #     else:
    #         return BaseAdapter(dev_name, self._dev_factory.get_device(dev_name))

    @property
    def input_parameter(self):
        """
        Return the input parameter

        :return: input parameter
        :rtype InputParameter
        """
        return self._input_parameter

    # @input_parameter.setter
    # def input_parameter(self, value):
    #     """
    #     Set the input parameter

    #     :param adapter: input parameter
    #     :type adapter: InputParameter
    #     """
    #     self._input_parameter = value

    @property
    def component(self):
        """
        Return the managed component  

        :return: the managed component
        :rtype Component
        """
        return self._component

    @property
    def devices(self):
        """
        Return the list of the monitored devices 

        :return: list of the monitored devices
        """
        return self._component.devices

    @property
    def checked_devices(self):
        """
        Return the list of the checked monitored devices 

        :return: list of the checked monitored devices
        """
        result = []
        for dev in self.component.devices:
            if dev.faulty:
                result.append(dev)
                continue
            if dev.ping > 0:
                result.append(dev)
                continue
            if dev.last_event_arrived is not None:
                result.append(dev)
                continue
        return result

    def get_device(self, dev_name):
        """
        Return the device info our of the monitoring loop with name dev_name

        :param dev_name: name of the device
        :type dev_name: str
        :return: a device info
        :rtype: DeviceInfo
        """
        return self.component.get_device(dev_name)

    def add_dishes(self, dln_prefix, num_dishes):
        """
        Add dishes to the monitoring loop

        :param dln_prefix: prefix of the dish
        :type dln_prefix: str
        :param num_dishes: number of dishes
        :type num_dishes: int
        """
        for dish in range(1, (num_dishes + 1)):
            self.add_device(dln_prefix + f"000{dish}")

    def add_multiple_devices(self, device_list):
        """
        Add multiple devices to the monitoring loop

        :param device_list: list of device names
        :type list: list[str]
        """
        for dev_name in device_list:
            self.add_device(dev_name)

    def add_device(self, dev_name):
        """
        Add device to the monitoring loop

        :param dev_name: device name
        :type dev_name: str
        """
        if dev_name is None:
            return
            
        if "subarray" in dev_name.lower():
            devInfo = SubArrayDeviceInfo(dev_name, False)
        else:
            devInfo = DeviceInfo(dev_name, False)

        self.component.update_device(devInfo)

    def add_command_execution(self, command_name, result_code, message):
        """
        Add a command execution to the list of the command executed
        """
        self._command_executed.append({
            "Command": command_name,
            "ResultCode": result_code,
            "Message" : message
        })
    
    def device_failed(self, device_info, exception):
        """
        Set a device to failed and call the relative callback if available

        :param device_info: a device info
        :type device_info: DeviceInfo
        :param exception: an exception
        :type Exception
        """
        with device_info.lock:
            self.component.update_device_exception(device_info, exception)

    def update_device_info(self, device_info):
        """
        Update a device with correct monitoring information
        and call the relative callback if available

        :param device_info: a device info
        :type device_info: DeviceInfo
        """
        with device_info.lock:
            self.component.update_device(device_info)

        self._aggregate_health_state()
        self._aggregate_state()

    def update_device_health_state(self, dev_name, health_state):
        """
        Update a monitored device health state
        aggregate the health states available

        :param dev_name: name of the device
        :type dev_name: str
        :param health_state: health state of the device
        :type health_state: HealthState
        """
        devInfo = self.component.get_device(dev_name)
        with devInfo.lock:
            devInfo.healthState = health_state
            devInfo.last_event_arrived = time.time()

        self._aggregate_health_state()

    def update_device_state(self, dev_name, state):
        """
        Update a monitored device state,
        aggregate the states available
        and call the relative callbacks if available

        :param dev_name: name of the device
        :type dev_name: str
        :param state: state of the device
        :type state: DevState
        """
        devInfo = self.component.get_device(dev_name)
        with devInfo.lock:
            devInfo.state = state
            devInfo.last_event_arrived = time.time()

        self._aggregate_state()

    def update_device_obs_state(self, dev_name, obs_state):
        """
        Update a monitored device obs state,
        and call the relative callbacks if available

        :param dev_name: name of the device
        :type dev_name: str
        :param obs_state: obs state of the device
        :type obs_state: ObsState
        """
        devInfo = self.component.get_device(dev_name)
        with devInfo.lock:
            devInfo.obsState = obs_state
            devInfo.last_event_arrived = time.time()
            self._update_resources(dev_name)

    def _aggregate_health_state(self):
        """
        Aggregates all health states 
        and call the relative callback if available
        """
        # import debugpy; debugpy.debug_this_thread()
        healthStateList = []
        # get states of CspMaster, SdpMaster and DishMaster devices
        # what if one of them is not working (i.e. faulty flag)? i.e. Csp, Sdp or dishes
        # number of dishes is also variable
        for dev in self.checked_devices:
            name = dev.dev_name.lower()
            if "leaf" in name:
                continue
            if "csp" in name and "master" in name:
                healthStateList.append(dev.healthState)
            if "sdp" in name and "master" in name:
                healthStateList.append(dev.healthState)
            if "tm" in name and "subarray" in name:
                healthStateList.append(dev.healthState)

        healthStateSetList = set(healthStateList)
        if healthStateSetList == set([HealthState.OK]):
            with self.component.lock:
                self.component.telescope_health_state = HealthState.OK
        elif HealthState.FAILED in healthStateSetList:
            with self.component.lock:
                self.component.telescope_health_state = HealthState.FAILED
        elif HealthState.DEGRADED in healthStateSetList:
            with self.component.lock:
                self.component.telescope_health_state = HealthState.DEGRADED
        else:
            with self.component.lock:
                self.component.telescope_health_state = HealthState.UNKNOWN

    def _aggregate_state(self):
        """
        Aggregates both telescope state and tm op state
        """
        self._aggregate_telescope_state()
        self._aggregate_tm_op_state()

    def _aggregate_telescope_state(self):
        """
        Aggregates telescope state
        """
        # import debugpy; debugpy.debug_this_thread()
        telescopeStateList = []
        # get states of CspMaster, SdpMaster and DishMaster devices
        # what if one of them is not working (i.e. faulty flag)? i.e. Csp, Sdp or dishes
        # number of dishes is also variable: at least one?
        for dev in self.checked_devices:
            name = dev.dev_name.lower()
            # if dev.faulty:
                # what I do?
            if "leaf" in name:
                continue
            elif "csp" in name and "master" in name:
                telescopeStateList.append(dev.state)
            elif "sdp" in name and "master" in name:
                telescopeStateList.append(dev.state)
            elif "mid_d" in name and "master" in name:
                telescopeStateList.append(dev.state)

        telescopeSetStateList = set(telescopeStateList)
        if telescopeSetStateList == set([DevState.ON]):
            with self.component.lock:
                self.component.telescope_state = DevState.ON
        elif telescopeSetStateList == set([DevState.OFF]):
            with self.component.lock:
                self.component.telescope_state = DevState.OFF
        elif DevState.INIT in telescopeSetStateList:
            with self.component.lock:
                self.component.telescope_state = DevState.INIT
        elif DevState.FAULT in telescopeSetStateList:
            with self.component.lock:
                self.component.telescope_state = DevState.FAULT
        elif DevState.STANDBY in telescopeSetStateList:
            with self.component.lock:
                self.component.telescope_state = DevState.STANDBY
        else:
            with self.component.lock:
                self.component.telescope_state = DevState.UNKNOWN

    def _aggregate_tm_op_state(self):
        """
        Aggregates tm devices states
        """
        tmStateList = []
        # get states of all TM devices
        # what if one of them is not working? i.e. tm subarray
        # number of devices is also variable, how to handle that number
        for dev in self.checked_devices:
            name = dev.dev_name.lower()
            if "tm" in name:
                tmStateList.append(dev.state)

        tmSetStateList = set(tmStateList)
        if tmSetStateList == set([DevState.ON]):
            with self.component.lock:
                self.component.tmc_op_state = DevState.ON
        elif tmSetStateList == set([DevState.OFF]):
            raise Exception("OFF State not allowed")
        elif DevState.INIT in tmSetStateList:
            with self.component.lock:
                self.component.tmc_op_state = DevState.INIT
        elif DevState.FAULT in tmSetStateList:
            with self.component.lock:
                self.component.tmc_op_state = DevState.FAULT
        elif DevState.STANDBY in tmSetStateList:
            with self.component.lock:
                self.component.tmc_op_state = DevState.STANDBY
        else:
            with self.component.lock:
                self.component.tmc_op_state = DevState.UNKNOWN

    def _update_resources(self, subarray_dev_name):
        """
        Updates resources for a subarray 
        the relative callback if available

        :param subarray_dev_name: name of the subarray device
        :type subarray_dev_name: str
        """
        pass


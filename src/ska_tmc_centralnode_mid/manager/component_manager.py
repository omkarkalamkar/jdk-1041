"""
This module provided a reference implementation of a BaseComponentManager.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import time
from tango import DevState
from ska_tango_base.base import BaseComponentManager
from ska_tango_base.control_model import HealthState, ObsState
from ska_tmc_centralnode_mid.manager.aggregators import TelescopeStateAggragator, HealthStateAggragator, TMCOpStateAggragator
from ska_tmc_centralnode_mid.model.component import Component, DeviceInfo, SubArrayDeviceInfo
from ska_tmc_centralnode_mid.manager.monitoring_loop import MonitoringLoop
from ska_tmc_centralnode_mid.manager.event_receiver import EventReceiver
from ska_tmc_centralnode_mid.manager.command_executor import CommandExecutor

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
        
        self._input_parameter = InputParameter(None)
        
        self._telescope_state_aggregator = None
        self._health_state_aggregator = None
        self._tm_op_state_aggregator = None

        self._command_executor = CommandExecutor(logger)
        self._command_executor.start()

    def set_aggregators(self, _telescope_state_aggregator, _health_state_aggregator, _tm_op_state_aggregator):
        self._telescope_state_aggregator = _telescope_state_aggregator
        self._health_state_aggregator = _health_state_aggregator
        self._tm_op_state_aggregator = _tm_op_state_aggregator

    @property
    def input_parameter(self):
        """
        Return the input parameter

        :return: input parameter
        :rtype InputParameter
        """
        return self._input_parameter

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

    @property
    def command_in_progress(self):
        return self._command_executor.command_in_progress

    @property
    def command_executor(self):
        return self._command_executor

    @property
    def command_executed(self):
        return self._command_executor._command_executed

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
        result = []
        for dish in range(1, (num_dishes + 1)):
            self.add_device(dln_prefix + f"000{dish}")
            result.append(dln_prefix + f"000{dish}")
        return result

    def add_multiple_devices(self, device_list):
        """
        Add multiple devices to the monitoring loop

        :param device_list: list of device names
        :type list: list[str]
        """
        result = []
        for dev_name in device_list:
            self.add_device(dev_name)
            result.append(dev_name)
        return result

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

    def update_input_parameter(self):
        list_dev_names = []
        for dev_name in self.input_parameter.tm_dish_dev_names:
            if self.get_device(dev_name) is None:
                self.add_device(dev_name)
                list_dev_names.append(dev_name)

        for dev_name in self.input_parameter.tm_subarray_dev_names:
            if self.get_device(dev_name) is None:
                self.add_device(dev_name)
                list_dev_names.append(dev_name)

        for dev_name in self.input_parameter.csp_subarray_dev_names:
            if self.get_device(dev_name) is None:
                self.add_device(dev_name)
                list_dev_names.append(dev_name)

        for dev_name in self.input_parameter.sdp_subarray_dev_names:
            if self.get_device(dev_name) is None:
                self.add_device(dev_name)
                list_dev_names.append(dev_name)
        
        dev_name = self.input_parameter.csp_master_dev_name
        if dev_name != "" and self.get_device(dev_name) is None:
            self.add_device(dev_name)
            list_dev_names.append(dev_name)

        dev_name = self.input_parameter.tm_leaf_csp_master_dev_name
        if dev_name != "" and self.get_device(dev_name) is None:
            self.add_device(dev_name)
            list_dev_names.append(dev_name)

        dev_name = self.input_parameter.sdp_master_dev_name
        if dev_name != "" and self.get_device(dev_name) is None:
            self.add_device(dev_name)
            list_dev_names.append(dev_name)
        
        dev_name = self.input_parameter.tm_leaf_sdp_master_dev_name
        if dev_name != "" and self.get_device(dev_name) is None:
            self.add_device(dev_name)
            list_dev_names.append(dev_name)

        for devInfo in self.devices:
            if devInfo.dev_name not in list_dev_names:
                self.component.remove_device(devInfo.dev_name) 
    
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
            self._update_resources(devInfo)

    
    def is_already_assigned(self, dishId):
        """
        Check if a Dish is already assigned to a subarray

        :param dishId: id of the dish
        :type dishId: str

        :return True is already assigned, False otherwise
        """
        for devInfo in self.devices:
            if isinstance(devInfo, SubArrayDeviceInfo):
                if dishId in devInfo.resources:
                    return True

        return False

    def _aggregate_health_state(self):
        """
        Aggregates all health states 
        and call the relative callback if available
        """
        if self._health_state_aggregator is None:
            self._health_state_aggregator = HealthStateAggragator(self)

        new_state = self._health_state_aggregator.aggregate()
        with self.component.lock:
            self.component.telescope_health_state = new_state

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
        if self._telescope_state_aggregator is None:
            self._telescope_state_aggregator = TelescopeStateAggragator(self)

        new_state = self._telescope_state_aggregator.aggregate()
        with self.component.lock:
            self.component.telescope_state = new_state

    def _aggregate_tm_op_state(self):
        """
        Aggregates tm devices states
        """
        if self._tm_op_state_aggregator is None:
            self._tm_op_state_aggregator = TMCOpStateAggragator(self)

        new_state = self._tm_op_state_aggregator.aggregate()
        with self.component.lock:
            self.component.tmc_op_state = new_state

    def _update_resources(self, subarray_dev_info):
        """
        Updates resources for a subarray 
        the relative callback if available

        :param subarray_dev_name: name of the subarray device
        :type subarray_dev_name: str
        """
        if self._monitoring_loop is not None:
            self._monitoring_loop.add_priority_devices(subarray_dev_info.dev_name)
        else:
            # If the monitoring loop is not active
            # I must assume that the subarray is reporting the correct value
            # and I need to update the assigned resources in the device info
            if subarray_dev_info.obsState == ObsState.EMPTY:
                subarray_dev_info.resources = []

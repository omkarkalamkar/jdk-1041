"""
This module provided a reference implementation of a BaseComponentManager.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import threading
import time
from typing import Callable

from ska_tango_base.control_model import ObsState
from ska_tmc_common.command_executor import CommandExecutor
from ska_tmc_common.device_info import DeviceInfo, SubArrayDeviceInfo
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.liveliness_probe import MultiDeviceLivelinessProbe
from ska_tmc_common.tmc_component_manager import TmcComponentManager
from tango import DevState

from ska_tmc_centralnode.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode.manager.aggregators import (
    HealthStateAggregatorLow,
    HealthStateAggregatorMid,
    TelescopeStateAggregatorLow,
    TelescopeStateAggregatorMid,
    TMCOpStateAggregator,
)
from ska_tmc_centralnode.manager.event_receiver import CentralNodeEventReceiver
from ska_tmc_centralnode.model.component import CentralComponent
from ska_tmc_centralnode.model.enum import ModesAvailability
from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)


class CNComponentManager(TmcComponentManager):
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

    def __init__(
        self,
        _input_parameter,
        logger=None,
        _component=None,
        _liveliness_probe=True,
        _event_receiver=True,
        _update_device_callback=None,
        _update_telescope_state_callback=None,
        _update_telescope_health_state_callback=None,
        _update_tmc_op_state_callback=None,
        _update_imaging_callback=None,
        _update_command_in_progress_callback=None,
        communication_state_callback=None,
        component_state_callback=None,
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
        *args,
        **kwargs,
    ):
        """
        Initialise a new ComponentManager instance.

        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        """
        self.logger = logger
        self.lock = threading.Lock()
        self._component = _component or CentralComponent(logger)
        self._input_parameter = _input_parameter

        self._liveliness_probe = None
        if _liveliness_probe:
            self._liveliness_probe = MultiDeviceLivelinessProbe(
                self,
                logger,
                max_workers=max_workers,
                proxy_timeout=proxy_timeout,
                sleep_time=sleep_time,
            )
            self._liveliness_probe.start()
        else:
            self.logger.warning("Liveliness Probe is not running")

        self._event_receiver = None
        if _event_receiver:
            self._event_receiver = CentralNodeEventReceiver(
                self,
                logger,
                proxy_timeout=proxy_timeout,
                sleep_time=sleep_time,
            )
            self._event_receiver.start()
        else:
            self.logger.warning("Event Receiver is not running")

        self._component.set_op_callbacks(
            _update_device_callback,
            _update_telescope_state_callback,
            _update_telescope_health_state_callback,
            _update_tmc_op_state_callback,
            _update_imaging_callback,
        )
        super().__init__(
            _input_parameter=self._input_parameter,
            logger=self.logger,
            _component=self._component,
            _event_receiver=True,
            _liveliness_probe=True,
            communication_state_callback=None,
            component_state_callback=None,
            max_workers=5,
            proxy_timeout=500,
            sleep_time=1,
            *args,
            **kwargs,
        )

        self._telescope_state_aggregator = None
        self._health_state_aggregator = None
        self._tm_op_state_aggregator = None

        # TODO: This can be done as a part of CommandExecutor refactor separate story
        self._command_executor = CommandExecutor(
            logger,
            _update_command_in_progress_callback=_update_command_in_progress_callback,
        )

    def reset(self):
        pass

    def stop(self):
        self._liveliness_probe.stop()
        self._event_receiver.stop()
        self._command_executor.stop()

    def set_aggregators(
        self,
        _telescope_state_aggregator,
        _health_state_aggregator,
        _tm_op_state_aggregator,
    ):
        self._telescope_state_aggregator = _telescope_state_aggregator
        self._health_state_aggregator = _health_state_aggregator
        self._tm_op_state_aggregator = _tm_op_state_aggregator

    @property
    def input_parameter(self):
        """
        Return the input parameter

        :return: input parameter
        :rtype: InputParameter
        """
        return self._input_parameter

    @property
    def component(self):
        """
        Return the managed component

        :return: the managed component
        :rtype: Component
        """
        return self._component

    @property
    def devices(self):
        """
        Return the list of the monitored devices

        :return: list of the monitored devices
        """
        return self._component._devices

    @property
    def checked_devices(self):
        """
        Return the list of the checked monitored devices

        :return: list of the checked monitored devices
        """
        result = []
        for dev in self.component._devices:
            if dev.unresponsive:
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

    def check_if_csp_mln_is_responsive(self):
        return self._check_if_device_is_responsive(
            [self.input_parameter.tm_leaf_csp_master_dev_name]
        )

    def check_if_sdp_mln_is_responsive(self):
        return self._check_if_device_is_responsive(
            [self.input_parameter.tm_leaf_sdp_master_dev_name]
        )

    def check_if_subarrays_are_responsive(self):
        return self._check_if_device_is_responsive(
            self.input_parameter.tm_subarray_dev_names
        )

    def check_if_dishes_are_responsive(self):
        return self._check_if_device_is_responsive(
            self.input_parameter.tm_dish_dev_names
        )

    def check_if_mccs_mln_is_responsive(self):
        return self._check_if_device_is_responsive(
            [self.input_parameter.mccs_master_leaf_node]
        )

    def _check_if_device_is_responsive(self, dev_names):
        count = 0
        for dev_name in dev_names:
            dev_info = self.get_device(dev_name)
            if dev_info is not None and not dev_info.unresponsive:
                count += 1
        if count == 0:
            raise CommandNotAllowed(f"{dev_names} not available")

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
        with self.lock:
            self.input_parameter.update(self)

    def device_failed(self, device_info, exception):
        """
        Set a device to failed and call the relative callback if available

        :param device_info: a device info
        :type device_info: DeviceInfo
        :param exception: an exception
        :type: Exception
        """
        with self.lock:
            self.component.update_device_exception(device_info, exception)

    def update_event_failure(self, dev_name):
        with self.lock:
            devInfo = self.component.get_device(dev_name)
            devInfo.last_event_arrived = time.time()
            devInfo.update_unresponsive(False)

    def update_device_health_state(self, dev_name, health_state):
        """
        Update a monitored device health state
        aggregate the health states available

        :param dev_name: name of the device
        :type dev_name: str
        :param health_state: health state of the device
        :type health_state: HealthState
        """
        with self.lock:
            devInfo = self.component.get_device(dev_name)
            devInfo.health_state = health_state
            devInfo.last_event_arrived = time.time()
            devInfo.update_unresponsive(False)

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
        with self.lock:
            devInfo = self.component.get_device(dev_name)
            devInfo.state = state
            devInfo.last_event_arrived = time.time()
            devInfo.update_unresponsive(False)

        self._aggregate_state()
        if isinstance(self.input_parameter, InputParameterMid):
            self._update_imaging()

    def update_device_obs_state(self, dev_name, obs_state):
        """
        Update a monitored device obs state,
        and call the relative callbacks if available

        :param dev_name: name of the device
        :type dev_name: str
        :param obs_state: obs state of the device
        :type obs_state: ObsState
        """
        with self.lock:
            devInfo = self.component.get_device(dev_name)
            devInfo.obs_state = obs_state
            devInfo.last_event_arrived = time.time()
            devInfo.update_unresponsive(False)
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
            if isinstance(self._input_parameter, InputParameterLow):
                self._health_state_aggregator = HealthStateAggregatorLow(
                    self, self.logger
                )
            elif isinstance(self._input_parameter, InputParameterMid):
                self._health_state_aggregator = HealthStateAggregatorMid(
                    self, self.logger
                )
            else:
                pass

        with self.lock:
            self.component.telescope_health_state = (
                self._health_state_aggregator.aggregate()
            )

    def get_telescope_health_state(self):
        return self.component.telescope_health_state

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
            if isinstance(self._input_parameter, InputParameterLow):
                self._telescope_state_aggregator = TelescopeStateAggregatorLow(
                    self, self.logger
                )
            elif isinstance(self._input_parameter, InputParameterMid):
                self._telescope_state_aggregator = TelescopeStateAggregatorMid(
                    self, self.logger
                )
            else:
                pass

        with self.lock:
            new_state = self._telescope_state_aggregator.aggregate()
            self.component.telescope_state = new_state

    def get_telescope_state(self):
        return self.component.telescope_state

    def _aggregate_tm_op_state(self):
        """
        Aggregates tm devices states
        """
        if self._tm_op_state_aggregator is None:
            self._tm_op_state_aggregator = TMCOpStateAggregator(
                self, self.logger
            )

        with self.lock:
            self.component.tmc_op_state = (
                self._tm_op_state_aggregator.aggregate()
            )

    def get_tmc_op_state(self):
        return self.component.tmc_op_state

    # TODO: Modify below method as a part of EventReceiver refactoring
    def _update_resources(self, subarray_dev_info):
        """
        Updates resources for a subarray
        the relative callback if available

        :param subarray_dev_name: name of the subarray device
        :type subarray_dev_name: str
        """
        if self._liveliness_probe is not None:
            self._liveliness_probe.add_device(subarray_dev_info.dev_name)
        else:
            # If the monitoring loop is not active
            # I must assume that the subarray is reporting the correct value
            # and I need to update the assigned resources in the device info
            if subarray_dev_info.obs_state == ObsState.EMPTY:
                subarray_dev_info.resources = []

    def _update_imaging(self):
        """
        Checks if CSP is ON and if atleast one Dish is ON. If both the conditions are true,
        it sets imaging to be available.
        """
        dish_on = False
        csp_state = DevState.UNKNOWN
        with self.lock:
            for dev_name in self.input_parameter.dish_dev_names:
                dish = self.get_device(dev_name)
                if (
                    dish is not None
                    and not dish.unresponsive
                    and dish.state == DevState.ON
                ):
                    dish_on = True
                    break

            csp_master_device = self.get_device(
                self.input_parameter.csp_master_dev_name
            )
            if (
                csp_master_device is not None
                and not csp_master_device.unresponsive
            ):
                csp_state = csp_master_device.state

            if csp_state == DevState.ON and dish_on:
                self.component.imaging = ModesAvailability.available
            else:
                self.component.imaging = ModesAvailability.not_available

    def telescope_on(self, task_callback: Callable = None):
        """
        Turn the Telescope On.

        :return: a result code and message
        """
        telescopon_command = TelescopeOn(
            self, adapter_factory=None, logger=self.logger
        )

        task_status, responce = self.submit_task(
            telescopon_command.telescope_on,
            args=[self.logger],
            task_callback=task_callback,
        )
        return task_status, responce

    def telescope_off(self, task_callback: Callable = None):
        """
        Turn the Telescope Off.

        :return: a result code and message
        """
        telescopoff_command = TelescopeOff(
            self, adapter_factory=None, logger=self.logger
        )

        task_status, responce = self.submit_task(
            telescopoff_command.telescope_off,
            args=[self.logger],
            task_callback=task_callback,
        )
        return task_status, responce

    def is_command_allowed(self, command_name=None):
        if command_name in ["TelescopeOn", "TelescopeOff"]:
            if self.op_state_model.op_state in [
                DevState.FAULT,
                DevState.UNKNOWN,
                DevState.DISABLE,
            ]:
                raise CommandNotAllowed(
                    "Command is not allowed in current state %s",
                    self.op_state_model.op_state,
                )
        return True

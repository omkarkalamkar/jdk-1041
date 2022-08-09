"""
This module provided a reference implementation of a BaseComponentManager.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import time
from typing import Callable, Optional

import pandas as pd
from ska_tango_base.control_model import ObsState
from ska_tmc_common.adapters import AdapterFactory
from ska_tmc_common.device_info import DeviceInfo, SubArrayDeviceInfo
from ska_tmc_common.enum import LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed
from ska_tmc_common.tmc_component_manager import TmcComponentManager
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
)
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

    * Receiving the change events from lower level devices and trigger
      the TMC and telescope state aggregation
    """

    def __init__(
        self,
        op_state_model,
        _input_parameter,
        logger=None,
        _component=None,
        _liveliness_probe=LivelinessProbeType.MULTI_DEVICE,
        _event_receiver=True,
        _update_device_callback=None,
        _update_telescope_state_callback=None,
        _update_telescope_health_state_callback=None,
        _update_tmc_op_state_callback=None,
        _update_imaging_callback=None,
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

        :param op_state_model: the operational state model used by this component
            manager
        :param _input_parameter: allows to specify InputParameter class for TMC Mid or Low
        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        :param _liveliness_probe: allows to enable/disable LivelinessProbe usage
        :param _event_receiver: allows to enable/disable EventReceiver usage
        """

        self._component = _component or CentralComponent(logger)

        super().__init__(
            _input_parameter,
            logger,
            _component=self._component,
            _liveliness_probe=_liveliness_probe,
            _event_receiver=_event_receiver,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            max_workers=max_workers,
            proxy_timeout=proxy_timeout,
            sleep_time=sleep_time,
            *args,
            **kwargs,
        )
        self.op_state_model = op_state_model
        self.adapter_factory = AdapterFactory()

        if self.event_receiver:
            self.event_receiver_object = CentralNodeEventReceiver(
                self,
                logger=self.logger,
                proxy_timeout=self.proxy_timeout,
                sleep_time=self.sleep_time,
            )

        self.start_event_receiver()

        self._component.set_op_callbacks(
            _update_device_callback,
            _update_telescope_state_callback,
            _update_telescope_health_state_callback,
            _update_tmc_op_state_callback,
            _update_imaging_callback,
        )
        self._telescope_state_aggregator = None
        self._health_state_aggregator = None
        self._tm_op_state_aggregator = None

    def stop_event_receiver(self):
        if self.event_receiver:
            self.event_receiver_object.stop()

    def reset(self):
        pass

    def set_aggregators(
        self,
        _telescope_state_aggregator,
        _health_state_aggregator,
        _tm_op_state_aggregator,
    ):
        self._telescope_state_aggregator = _telescope_state_aggregator
        self._health_state_aggregator = _health_state_aggregator
        self._tm_op_state_aggregator = _tm_op_state_aggregator

    def stop(self):
        self.stop_liveliness_probe()
        self.stop_event_receiver()

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
        return self._component.devices

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

    def get_device(self, dev_name):
        """
        Return the device info with device name dev_name

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
        Add dishes to the liveliness probe function

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
        Add multiple devices to the liveliness probe function

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
        Add device to the liveliness probe function
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
            self.component._invoke_device_callback(devInfo)

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
            self.component._invoke_device_callback(devInfo)

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
            self.logger.debug(
                f"State event callback for device {dev_name}: {state}"
            )
            devInfo = self.component.get_device(dev_name)
            devInfo.state = state
            devInfo.last_event_arrived = time.time()
            devInfo.update_unresponsive(False)
            self.component._invoke_device_callback(devInfo)

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
            self.component._invoke_device_callback(devInfo)

    def update_device_assigned_resource(self, dev_name, assign_resources):
        """
        Update assign_resources for a monitored device

        :param dev_name: name of the device
        :type dev_name: str
        :param assign_resources: assign_resources
        :type assign_resources: str
        """
        with self.lock:
            dev_info = self.component.get_device(dev_name)
            dev_info.resources = assign_resources
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)
            self.component._invoke_device_callback(dev_info)

    def is_already_assigned(self, dish_id):
        """
        Check if a Dish is already assigned to a subarray

        :param dish_id: id of the dish
        :type dish_id: str

        :return True is already assigned, False otherwise
        """
        for devInfo in self.devices:
            if isinstance(devInfo, SubArrayDeviceInfo):
                if devInfo.resources is None:
                    return False
                elif dish_id in devInfo.resources:
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
        Aggregates both telescope state and tmc op state
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
        Aggregates TMC devices states
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

    # TODO: Kept it for reference. Not getting called anywhere.
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
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        task_status, response = self.submit_task(
            telescopon_command.telescope_on,
            args=[self.logger],
            task_callback=task_callback,
        )
        return task_status, response

    def telescope_off(self, task_callback: Callable = None):
        """
        Turn the Telescope Off.

        :return: a result code and message
        """
        telescope_off_command = TelescopeOff(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        task_status, response = self.submit_task(
            telescope_off_command.telescope_off,
            args=[self.logger],
            task_callback=task_callback,
        )
        return task_status, response

    def telescope_standby(self, task_callback: Callable = None):
        """
        Standby the Telescope.

        :return: a result code and message
        """
        telescopestandby_command = TelescopeStandby(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        task_status, response = self.submit_task(
            telescopestandby_command.telescope_standby,
            args=[self.logger],
            task_callback=task_callback,
        )
        return task_status, response

    def assign_resources(
        self, argin, task_callback: Optional[Callable] = None
    ):
        """
        Submit the AssignResources command in queue.

        :return: a result code and message
        """
        assign_resources_command = AssignResources(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )
        task_status, response = self.submit_task(
            assign_resources_command.assign_resources,
            args=[argin, self.logger],
            task_callback=task_callback,
        )
        return task_status, response

    def is_command_allowed(self, command_name=None):
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the
        component needed for the operation are not unresponsive

        :param command_name: name of the command
        :type command_name: str
        :return: True if this command is allowed

        :rtype: boolean
        """
        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                "Command is not allowed in current state %s",
                str(self.op_state_model.op_state),
            )
        if command_name in ["TelescopeOn", "TelescopeOff"]:
            if isinstance(self._input_parameter, InputParameterMid):
                self.logger.debug(f"Checking mid devices for {command_name}")
                self.check_if_csp_mln_is_responsive()
                self.check_if_sdp_mln_is_responsive()
                self.check_if_subarrays_are_responsive()
                self.check_if_dishes_are_responsive()
            else:
                self.logger.debug(f"Checking low devices for {command_name}")
                self.check_if_mccs_mln_is_responsive()
                self.check_if_subarrays_are_responsive()
        elif command_name in ["AssignResources", "ReleaseResources"]:
            if isinstance(self._input_parameter, InputParameterMid):
                self.logger.debug(f"Checking mid devices for {command_name}")
                self.check_if_subarrays_are_responsive()
                self.check_if_dishes_are_responsive()
            else:
                self.logger.debug(f"Checking low devices for {command_name}")
                self.check_if_mccs_mln_is_responsive()
                self.check_if_subarrays_are_responsive()

        return True

    def log_state(self, msg="Device States"):
        device_names = []
        dev_states = []

        for device in self.component_manager.devices:
            device_names.append(device.dev_name)
            dev_states.append(device.state)

        device_states = pd.DataFrame(
            {"Devices": device_names, "STATE": dev_states}
        )
        self.logger.info("\n" + msg + "\n" + device_states.to_string() + "\n")

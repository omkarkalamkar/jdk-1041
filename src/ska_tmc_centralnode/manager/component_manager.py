"""
This module provided an implementation of the Central Node ComponentManager.
"""

from __future__ import annotations

import json
import re
import threading
import time
import traceback
from collections import defaultdict
from logging import Logger
from multiprocessing import Event
from multiprocessing import Lock as ProcessLock
from multiprocessing import Manager
from queue import Empty, Queue
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import tango
from ska_control_model import AdminMode, HealthState, TaskStatus
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.control_model import ObsState
from ska_tango_base.faults import StateModelError
from ska_tmc_common import (
    AdapterFactory,
    AdapterType,
    Aggregator,
    CommandNotAllowed,
    DeviceInfo,
    DishDeviceInfo,
    InvalidJSONError,
    LivelinessProbeType,
    LRCRCallback,
    SubArrayDeviceInfo,
    SubarrayNotPresentError,
)
from ska_tmc_common.v2.tmc_component_manager import TmcComponentManager
from tango import DevState
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from ska_tmc_centralnode.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
)
from ska_tmc_centralnode.manager.aggregators import TMCOpStateAggregator
from ska_tmc_centralnode.manager.event_data_manager import EventDataManager
from ska_tmc_centralnode.manager.event_manager import CentralNodeEventManager
from ska_tmc_centralnode.model.component import (
    CentralComponent,
    MCCSDeviceInfo,
)
from ska_tmc_centralnode.model.enum import ModesAvailability
from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)
from ska_tmc_centralnode.utils.constants import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MCCS_MLN_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
)


class CNComponentManager(TmcComponentManager):
    """
    A component manager for The Central Node component.

    It supports:

    1. Monitoring its component, e.g. detect that it has been turned off
    or on\n

    2. Receiving the change events from lower level devices and trigger
    the TMC and telescope state aggregation
    """

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        op_state_model,
        _input_parameter,
        logger: Logger,
        _update_device_callback: Callable,
        _update_telescope_state_callback: Callable,
        _update_telescope_health_state_callback: Callable,
        _update_tmc_op_state_callback: Callable,
        _update_imaging_callback: Callable,
        _telescope_availability_callback: Callable,
        array_layout_url_callback: Callable,
        default_array_layout_url_callback: Callable,
        _component=None,
        _liveliness_probe=LivelinessProbeType.MULTI_DEVICE,
        _event_manager: bool = True,
        proxy_timeout=500,
        event_subscription_check_period=1,
        liveliness_check_period=1,
        command_timeout=30,
        retry_attempts: int = 5,
        retry_delay: float = 3.0,
        subarray_trl_prefix: str = "",
        default_array_layout_url: dict | None = None,
        *args,
        **kwargs,
    ):
        """
        Initialise a new ComponentManager instance.

        :param op_state_model: the operational state model used
            by this component manager
        :param _input_parameter: allows to specify InputParameter
            class for TMC Mid or Low
        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        :param _liveliness_probe: allows to enable/disable
            LivelinessProbe usage
        :param _event_manager: allows to enable/disable
            EventManager usage

        """

        self._component = _component or CentralComponent(logger)
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.subarray_trl_prefix = subarray_trl_prefix
        super().__init__(
            _input_parameter,
            logger,
            _component=self._component,
            _liveliness_probe=_liveliness_probe,
            _event_manager=False,
            proxy_timeout=proxy_timeout,
            event_subscription_check_period=event_subscription_check_period,
            liveliness_check_period=liveliness_check_period,
            *args,
            **kwargs,
        )
        self.op_state_model = op_state_model
        self.adapter_factory = AdapterFactory()
        self.event_data_manager = EventDataManager(self)
        self.event_manager: bool = _event_manager
        self.command_timeout = command_timeout
        self.process_lock = ProcessLock()
        self._component.set_op_callbacks(
            _update_device_callback,
            _update_telescope_state_callback,
            _update_telescope_health_state_callback,
            _update_tmc_op_state_callback,
            _update_imaging_callback,
            _telescope_availability_callback,
        )
        self._assign_resources_schema_version = ""
        self._release_resources_schema_version = ""
        self._telescope_state_aggregator = None
        self._health_state_aggregator = None
        self._op_state_aggregator = None
        self.long_running_result_callback = LRCRCallback(self.logger)
        self.command_in_progress: str = ""
        self.command_mapping = {}
        self.result_codes_mapping = {}
        self.rlock = threading.RLock()
        self.no_of_events_for_command = 0

        self.supported_commands = (
            "AssignResources",
            "ReleaseResources",
            "ReleaseAllResources",
        )
        self._telescope_availability_aggregator = Aggregator(
            self, logger=logger
        )
        self._stop_thread: bool = False
        self._liveliness_probe = None
        self.supported_commands_for_responsive_check = [
            "TelescopeOn",
            "TelescopeOff",
            "TelescopeStandby",
            "AssignResources",
            "ReleaseResources",
        ]
        self.__event_queue: Dict[str, Queue] = {
            "obsState": Queue(),
            "assignedResources": Queue(),
            "healthState": Queue(),
            "adminMode": Queue(),
        }

        self.event_processing_methods: Dict[
            str, Callable[[str, Any], None]
        ] = {
            "obsState": self.update_device_obs_state,
            "assignedResources": self.update_device_assigned_resource,
            "healthState": self.update_device_health_state,
            "adminMode": self.update_device_admin_mode,
        }
        self.aggregate_process_manager = Manager()
        self.event_data_queue = self.aggregate_process_manager.Queue()
        self.aggregated_health_state = self.aggregate_process_manager.list(
            [""]
        )
        self.aggregate_value_update_event = Event()
        self.aggregate_process_monitor_thread = threading.Thread(
            target=self.aggregate_process_monitor
        )
        self.aggregate_process_monitor_thread.start()
        self.event_manager_object: CentralNodeEventManager = (
            CentralNodeEventManager(self, logger=logger)
        )
        self._array_layout_url: str = ""
        self._array_layout_url_callback = array_layout_url_callback
        self._default_array_layout_url_callback = (
            default_array_layout_url_callback
        )
        self._default_array_layout_url: dict = default_array_layout_url
        self.command_completion_cond = threading.Condition()

    def setup_event_subscription(self) -> None:
        """
        Sets up the event subscription after input parameters are updated.
        """

        self.start_event_manager(
            self.build_device_attribute_map(), timeout=1000
        )
        if self.event_manager:
            self.event_manager_object.init_timeout(self.event_thread_id)
        self.logger.debug("Successfully subscribed the events")

    def build_device_attribute_map(self) -> Dict[str, List[str]]:
        """
        Builds a dictionary mapping device names to lists of attributes
        to be subscribed.

        Returns:
            Dict[str, List[str]]: A mapping from device names to list of
            attributes.
        """
        device_attribute_map = defaultdict(list)

        # Define subsystem devices once
        subsystem_devices = [
            MID_CSP_MLN_DEVICE,
            MID_SDP_MLN_DEVICE,
            LOW_CSP_MLN_DEVICE,
            LOW_SDP_MLN_DEVICE,
            MCCS_MLN_DEVICE,
        ]

        for dev_info in self.devices:
            dev_name = dev_info.dev_name
            # Add basic attributes to all devices
            device_attribute_map[dev_name].extend(
                [
                    "state",
                    "healthState",
                    "adminMode",
                ]
            )

            # Subarray-specific attributes (excluding leaf nodes)
            if "subarray" in dev_name and "leaf" not in dev_name:
                device_attribute_map[dev_name].extend(
                    [
                        "assignedResources",
                        "obsState",
                    ]
                )

            # Dish leaf node-specific attributes
            if (
                isinstance(self.input_parameter, InputParameterMid)
                and dev_name in self.input_parameter.dish_leaf_node_dev_names
            ):
                device_attribute_map[dev_name].extend(
                    [
                        "dishMode",
                        "kValueValidationResult",
                        "healthState",
                        "gpmVersion",
                    ]
                )

            # Subarray dev-specific attributes
            if dev_name in self.input_parameter.subarray_dev_names:
                device_attribute_map[dev_name].extend(
                    [
                        "isSubarrayAvailable",
                    ]
                )

            # Subsystem availability attribute
            if dev_name in subsystem_devices:
                device_attribute_map[dev_name].append("isSubsystemAvailable")

        # Add specific subsystem attributes if present
        if MID_CSP_MLN_DEVICE in device_attribute_map:
            device_attribute_map[MID_CSP_MLN_DEVICE].extend(
                [
                    "DishVccMapValidationResult",
                    "cspControllerAdminMode",
                ]
            )
        if LOW_CSP_MLN_DEVICE in device_attribute_map:
            device_attribute_map[LOW_CSP_MLN_DEVICE].append(
                "cspControllerAdminMode"
            )
        if MID_SDP_MLN_DEVICE in device_attribute_map:
            device_attribute_map[MID_SDP_MLN_DEVICE].append(
                "sdpControllerAdminMode"
            )
        if LOW_SDP_MLN_DEVICE in device_attribute_map:
            device_attribute_map[LOW_SDP_MLN_DEVICE].append(
                "sdpControllerAdminMode"
            )
        if MCCS_MLN_DEVICE in device_attribute_map:
            device_attribute_map[MCCS_MLN_DEVICE].extend(
                [
                    "mccsControllerAdminMode",
                ]
            )
        self.logger.debug(
            "Device attribute map dictionary : %s", device_attribute_map
        )
        return device_attribute_map

    # ------------------------------------------------------------------
    # Array layout URL (current)
    # ------------------------------------------------------------------
    @property
    def array_layout_url(self) -> dict:
        """Get the current array layout URL (as a dict)."""
        return self._array_layout_url

    @array_layout_url.setter
    def array_layout_url(self, url: dict) -> None:
        """Set the current array layout URL."""
        if not isinstance(url, dict):
            raise ValueError("array_layout_url must be a dictionary.")
        if url == self._array_layout_url:
            # avoid redundant events/logs
            return
        self._array_layout_url = url
        self.logger.info("Array layout URL set to: %s", url)

        # >>> notify Tango device if callback is provided <<<
        if self._array_layout_url_callback is not None:
            self._array_layout_url_callback(url)

    # ------------------------------------------------------------------
    # Array layout URL (default)
    # ------------------------------------------------------------------
    @property
    def default_array_layout_url(self) -> dict:
        """Get the default array layout URL."""
        return self._default_array_layout_url

    @default_array_layout_url.setter
    def default_array_layout_url(self, url: dict) -> None:
        """Set the default array layout URL."""
        if not isinstance(url, dict):
            raise ValueError("default_array_layout_url must be a dictionary.")
        if url == self._default_array_layout_url:
            return
        self._default_array_layout_url = url
        self.logger.info("Default array layout URL set to: %s", url)

        if self._default_array_layout_url_callback is not None:
            self._default_array_layout_url_callback(url)

    @property
    def event_queue(self):
        """event queue property"""
        with self.rlock:
            return self.__event_queue

    def _start_event_processing_threads(self) -> None:
        """Start all the event processing threads."""
        for attribute in self.event_queue:
            thread = threading.Thread(
                target=self.process_event,
                args=[attribute],
                name=attribute,
                daemon=True,
            )
            thread.start()

    def aggregate_process_monitor(self):
        """This method keep tracking aggregate health state changed
        from aggregation process
        """

        while not self._stop_thread:
            if self.aggregate_value_update_event.wait(0.3):
                self.aggregate_value_update_event.clear()
                current_health_state = self.aggregated_health_state[0]
                self.component.telescope_health_state = current_health_state
                self.logger.debug(
                    "Aggregate telescope health state called %s",
                    str(current_health_state),
                )
        self.logger.debug("aggregation process monitor thread stopped")

    def process_event(self, attribute_name: str) -> None:
        """
        Process the given attribute's event using the data from the
            event_queue and invoke corresponding process method.

        :param attribute_name: Name of the attribute for which event is to be
            processed

        :type attribute_name: str

        :returns: None

        """
        while not self._stop_thread:
            try:
                event_data = self.event_queue[attribute_name].get()
                if not self.check_event_error(
                    event_data, f"{attribute_name}_Callback"
                ):
                    if attribute_name in ("healthState", "adminMode"):
                        self.event_processing_methods[attribute_name](
                            event_data.device.dev_name(),
                            event_data.attr_value.value,
                            event_data.attr_value.time.todatetime(),
                        )
                    else:
                        self.event_processing_methods[attribute_name](
                            event_data.device.dev_name(),
                            event_data.attr_value.value,
                        )
                self.event_queue[attribute_name].task_done()
            except Empty:
                # If an empty exception is raised by the Queue, we can
                # safely ignore it.
                pass
            except Exception as exception:
                self.logger.error(
                    "Exception: %s Traceback: %s",
                    exception,
                    traceback.print_exc(),
                )

    def check_event_error(self, event: tango.EventData, callback: str):
        """Method for checking event error."""
        if event.err:
            error = event.errors[0]
            self.logger.error(
                "Event error occurred on %s for device: %s - %s, %s",
                callback,
                event.device.dev_name(),
                error.reason,
                error.desc,
            )
            self.update_event_failure(event.device.dev_name())
            return True
        return False

    def stop_aggregation_process(self):
        """Override this method in mid and low"""
        raise NotImplementedError

    def stop_all_process(self):
        """This stop aggregation process"""
        with self.process_lock:
            self.stop_aggregation_process()
            del self.event_data_queue
            del self.aggregated_health_state
            self.aggregate_process_manager.shutdown()
            self.logger.debug("aggregation process stopped")

    def __del__(self):
        """shutdown aggregation process"""
        self.logger.debug("component destructor called")
        self.stop_all_process()
        self.stop()

    def cleanup(self):
        self.stop_all_process()
        self.stop()

    def stop_event_manager(self) -> None:
        """Stops the Event Receiver"""
        if self.event_manager:
            self.event_manager_object.cancel_subscription_thread(
                self.event_thread_id
            )
            try:
                subscriptions = (
                    self.event_manager_object.device_subscriptions.copy()
                )
                for device in subscriptions:
                    if subscriptions.get(device).get(
                        "is_subscription_completed"
                    ):
                        self.event_manager_object.unsubscribe_event_async(
                            device
                        )
            except Exception:
                self.logger.exception(
                    "Failed to unsubscribe event for %s", device
                )

    def stop(self) -> None:
        """stops liveliness probe"""
        self.stop_liveliness_probe()
        self.stop_event_manager()
        self._stop_thread = True

    def reset(
        self: CNComponentManager, task_callback: Optional[Callable] = None
    ) -> tuple[TaskStatus, str]:
        """
        Placeholder method for reset command.

        Args:
            task_callback: Update task status, defaults to None

        Returns:
            tuple(TaskStatus, str): task_status, message

        """
        return TaskStatus.REJECTED, "Reset command is not implemented"

    def set_aggregators(
        self,
        _telescope_state_aggregator,
        _health_state_aggregator,
        _op_state_aggregator,
    ) -> None:
        """Sets Aggregators callback"""
        self._telescope_state_aggregator = _telescope_state_aggregator
        self._health_state_aggregator = _health_state_aggregator
        self._op_state_aggregator = _op_state_aggregator

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
        return self.component.devices

    # pylint:disable =inconsistent-return-statements
    def get_subarray_obsstate(self, subarray_devname: str) -> ObsState:
        """
        Get Current device obsState

        Args:
            subarray_devname (str): subarray device name

        Returns:
            ObsState: current obsstate
        """
        if subarray_devname:
            return self.get_device(subarray_devname).obs_state

    def get_device(self, device_name):
        """
        Return the device info with device name dev_name

        :param dev_name: name of the device
        :type dev_name: str
        :return: a device info
        :rtype: DeviceInfo
        """
        return self.component.get_device(device_name)

    def get_sdp_subarray_dev_names(self) -> list:
        """
        Return Sdp Subarray device names
        """
        return self.input_parameter.sdp_subarray_dev_names

    def get_sdp_master_leaf_node_dev_name(self) -> str:
        """
        Return Sdp master leaf node device name
        """
        return self.input_parameter.sdp_mln_dev_name

    def get_csp_master_leaf_node_dev_name(self) -> str:
        """
        Return Csp master leaf node device name
        """
        return self.input_parameter.csp_mln_dev_name

    def get_csp_subarray_dev_names(self) -> list:
        """
        Return Csp Subarray device names
        """
        return self.input_parameter.csp_subarray_dev_names

    def get_sdp_master_dev_name(self) -> str:
        """
        Return Sdp Master device name
        """
        return self.input_parameter.sdp_master_dev_name

    def get_mccs_master_dev_name(self) -> str:
        """
        Return Sdp Master device name
        """
        return self.input_parameter.mccs_master_dev_name

    def get_mccs_master_leaf_node_dev_name(self) -> str:
        """
        Return MCCS master leaf node device name
        """
        return self.input_parameter.mccs_mln_dev_name

    def get_csp_master_dev_name(self) -> str:
        """
        Return Csp Master device name
        """
        return self.input_parameter.csp_master_dev_name

    def get_dish_device_names(self) -> tuple:
        """
        Return Dish Master device names
        """
        return self.input_parameter.dish_dev_names

    def get_dish_leaf_node_device_names(self) -> tuple:
        """
        Return Dish leaf node device names
        """
        return self.input_parameter.dish_leaf_node_dev_names

    def check_if_csp_mln_is_available(self) -> bool:
        """
        Returns boolean value based on availability of CspMasterLeafNode,
        which ultimately indicated availability of CspMasterNode
        """
        telescope_availability = self.get_telescope_availability()
        if not telescope_availability["csp_master_leaf_node"] is True:
            self.logger.info(
                "CspMasterLeafNode is not available to receive command"
            )
            return False

        return True

    def check_if_sdp_mln_is_available(self) -> bool:
        """
        Returns boolean value based on availability of SdpMasterLeafNode,
        which ultimately indicated availability of SdpMasterNode
        """
        telescope_availability = self.get_telescope_availability()
        if not telescope_availability["sdp_master_leaf_node"] is True:
            self.logger.info(
                "SdpMasterLeafNode is not available to receive command"
            )
            return False

        return True

    def check_if_subarrays_are_responsive(self) -> bool:
        """
        Checks if subarray are responsive

        :return: True if at least one subarray device is responsive,
                 False otherwise.
        :rtype: bool
        """
        self.logger.debug("Checking if subarrays are responsive")
        return self._check_if_device_is_responsive(
            self.input_parameter.subarray_dev_names
        )

    def check_if_subarray_is_responsive(self, subarray_id: int) -> bool:
        """
        Checks if subarray is responsive

        :param subarray_id: Subarray id
        :type subarray_id: int
        :return: True if the subarray device is responsive,
                 False otherwise.
        :rtype: bool
        """
        self.logger.debug("Checking if subarray %s is responsive", subarray_id)
        subarray_devices = self.input_parameter.subarray_dev_names
        for device in subarray_devices:
            subarray_device_id = re.findall(r"\d+", device)
            if subarray_id == int(subarray_device_id[0]):
                return self._check_if_device_is_responsive([device])
        return False

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(3.0),
        retry=retry_if_exception_type(
            (CommandNotAllowed, SubarrayNotPresentError)
        ),
        reraise=True,
    )
    def _check_if_device_is_responsive(self, dev_names: List[str]):
        """checks if the device is responsive"""
        self._check_if_device_is_responsive.retry.stop = stop_after_attempt(
            self.retry_attempts
        )
        self._check_if_device_is_responsive.retry.wait = wait_fixed(
            self.retry_delay
        )
        self.logger.debug("Retrying device responsive check")
        count = 0
        for dev_name in dev_names:
            dev_info = self.get_device(dev_name)
            if dev_info is not None and not dev_info.unresponsive:
                self.logger.debug(
                    f"Device {dev_name} dev_info.unresponsive:"
                    + f" {dev_info.unresponsive} "
                )
                count += 1
        # Raise SubarrayNotPresentError if fqdn matches subarray prefix,
        # else CommandNotAllowed
        if count == 0:
            if any(
                name.lower().startswith(self.subarray_trl_prefix)
                and "dish" not in name.lower()
                for name in dev_names
            ):
                raise SubarrayNotPresentError(
                    f"Subarray devices not available: {dev_names}"
                )
            raise CommandNotAllowed(f"{dev_names} not available")

    def add_multiple_devices(self, device_list: List[str]):
        """
        Add multiple devices to the liveliness probe function

        :param device_list: list of device names
        :type device_list: list[str]
        """
        result = []
        for dev_name in device_list:
            self.add_device(dev_name)
            result.append(dev_name)
        return result

    def add_device(self, device_name: str) -> None:
        """
        Add device to the liveliness probe function

        Args:
            dev_name (str): device name

        """
        if "subarray" in device_name.lower():
            devInfo = SubArrayDeviceInfo(device_name, False)
        elif (
            isinstance(self.input_parameter, InputParameterMid)
            and device_name in self.input_parameter.dish_leaf_node_dev_names
        ):
            devInfo = DishDeviceInfo(device_name, False)
        elif (
            isinstance(self.input_parameter, InputParameterLow)
            and device_name.lower() in self.input_parameter.mccs_mln_dev_name
        ):
            devInfo = MCCSDeviceInfo(device_name, False)
        else:
            devInfo = DeviceInfo(device_name, False)
        self.component.update_device(devInfo)
        if self.liveliness_probe_object:
            self.liveliness_probe_object.add_device(device_name)

    def update_input_parameter(self) -> None:
        """updates the input parameter for component manager instance"""
        with self.lock:
            self.input_parameter.update(self)

    def update_responsiveness_info(self, device_name: str) -> None:
        """
        Update a device with correct responsiveness information.

        Args:
            dev_name (str): name of the device

        """
        with self.rlock:
            dev_info = self.get_device(device_name)
            dev_info.update_unresponsive(False, "")
            self._telescope_availability_aggregator.aggregate()

    def update_exception_for_unresponsiveness(
        self, device_info: DeviceInfo, exception: Exception
    ) -> None:
        """
        Set a device to failed and call the relative callback if available.

        Args:
            device_info (DeviceInfo): Information about the device
            exception (Exception): Exception raised during the ping failure

        """
        # Log the device failure with the device name
        message = (
            f"Device: {device_info.dev_name} failed to respond: {exception}"
        )
        self.logger.error(message)

        with self.rlock:
            device_name = device_info.dev_name
            dev_info = self.component.get_device(device_name)
            # Update the device status with the exception details
            dev_info.update_unresponsive(True, str(exception))
            self._telescope_availability_aggregator.aggregate()

    def update_event_failure(self, device_name: str) -> None:
        """
        updates event failures in Dev info

        Args:
            device_name (str): Device name

        """
        with self.rlock:
            devInfo = self.component.get_device(device_name)
            devInfo.last_event_arrived = time.time()
            self.component._invoke_device_callback(devInfo)

    def update_device_health_state(
        self, device_name: str, health_state: HealthState, timestamp
    ) -> None:
        """
        Update a monitored device health state
        aggregate the health states available

        Args:
            dev_name (str): name of the device
            health_state (HealthState): health state of the device
            timstamp: timestamp

        """
        with self.lock:
            self.logger.debug(
                f"healthState event for {device_name}: "
                + f"{HealthState(health_state).name}"
            )
            if "sdp" in device_name:
                # Update SDP Master device name with full FQDN for real SDP
                sdp_master_dev_name = self.get_sdp_master_dev_name()
                if device_name in sdp_master_dev_name:
                    device_name = sdp_master_dev_name
            if "csp" in device_name:
                # Update CSP Master device name with full FQDN for real CSP
                csp_master_dev_name = self.get_csp_master_dev_name()
                if device_name in csp_master_dev_name:
                    device_name = csp_master_dev_name
            if isinstance(self.input_parameter, InputParameterMid):
                if self.input_parameter.dish_leaf_node_prefix in device_name:
                    dln_dev_names = self.get_dish_leaf_node_device_names()
                    for dish in dln_dev_names:
                        if device_name in dish.lower():
                            device_name = dish
                if self.input_parameter.dish_master_identifier in device_name:
                    # Update Dish Master device name with full FQDN in case of
                    # real Dish
                    dish_master_dev_names = self.get_dish_device_names()
                    for dish in dish_master_dev_names:
                        if device_name in dish.lower():
                            device_name = dish

            devInfo = self.component.get_device(device_name)
            if devInfo is not None:
                devInfo.health_state = health_state
                self.logger.debug(
                    "Updated healthState of %s: %s",
                    devInfo.dev_name,
                    HealthState(devInfo.health_state).name,
                )
                devInfo.last_event_arrived = time.time()
                self.event_data_manager.update_event_data(
                    device=device_name,
                    data=health_state,
                    received_timestamp=timestamp,
                    data_type="HealthState",
                )
                self.component._invoke_device_callback(devInfo)

    def update_device_admin_mode(
        self, device_name: str, admin_mode: AdminMode, timestamp
    ):
        """
        Update a monitored device admin mode

        :param device_name: name of the device
        :type device_name: str
        :param admin_mode: admin mode of the device
        :type admin_mode: AdminMode
        """
        self.logger.debug(
            f"AdminMode event for {device_name}: "
            + f"{AdminMode(admin_mode).name}"
        )
        with self.lock:
            leafnode_identifiers = [
                MID_SDP_MLN_DEVICE,
                MID_CSP_MLN_DEVICE,
                LOW_SDP_MLN_DEVICE,
                LOW_CSP_MLN_DEVICE,
                MCCS_MLN_DEVICE,
            ]
            if any(
                identifier in device_name.lower()
                for identifier in leafnode_identifiers
            ):
                device_info = self.component.get_device(device_name)
                if device_info is not None:
                    device_info.last_event_arrived = time.time()
                    device_info.admin_mode = admin_mode
                    self.event_data_manager.update_event_data(
                        device=device_name,
                        data=admin_mode,
                        data_type="AdminMode",
                        received_timestamp=timestamp,
                    )
                    self.component._invoke_device_callback(device_info)

    def update_device_obs_state(
        self, dev_name: str, obs_state: ObsState
    ) -> None:
        """
        Update a monitored device obs state,
        and call the relative callbacks if available

        :param dev_name: name of the device
        :type dev_name: str
        :param obs_state: obs state of the device
        :type obs_state: ObsState
        """
        with self.rlock:
            self.logger.debug(
                f"obsState event for {dev_name}: {ObsState(obs_state).name}"
            )
            sdp_subarray_dev_names = self.get_sdp_subarray_dev_names()
            for sdp_subarray in sdp_subarray_dev_names:
                if dev_name in sdp_subarray:
                    dev_name = sdp_subarray

            # TODO: Enable this fix when real CSP controller and CSP Subarray
            # exposes full FQDN, in integration
            # csp_subarray_dev_names = self.get_csp_subarray_dev_names()
            # for csp_subarray in csp_subarray_dev_names:
            #     if dev_name in csp_subarray:
            #         dev_name = csp_subarray

            devInfo = self.component.get_device(dev_name)
            if devInfo is not None:
                devInfo.obs_state = obs_state
                self.logger.debug(
                    "Updated ObsState of %s: %s",
                    devInfo.dev_name,
                    ObsState(devInfo.obs_state).name,
                )
                with self.command_completion_cond:
                    self.command_completion_cond.notify_all()
                devInfo.last_event_arrived = time.time()
                self.component._invoke_device_callback(devInfo)

    def update_device_assigned_resource(
        self, dev_name: str, assign_resources: str
    ) -> None:
        """
        Update assign_resources for a monitored device

        :param dev_name: name of the device
        :type dev_name: str
        :param assign_resources: assigned resources in JSON format
        :type assign_resources: str
        """
        with self.lock:
            self.logger.debug(
                "Updating assigned resources for device %s: %s",
                dev_name,
                assign_resources,
            )
            sdp_subarray_dev_name = self.get_sdp_subarray_dev_names()
            for sdp_subarray in sdp_subarray_dev_name:
                if dev_name in sdp_subarray:
                    dev_name = sdp_subarray
            # TODO: Enable this fix when real CSP controller and CSP Subarray
            # exposes full FQDN, in integration
            # csp_subarray_dev_names = self.get_csp_subarray_dev_names()
            # for csp_subarray in csp_subarray_dev_names:
            #     if dev_name in csp_subarray:
            #         dev_name = csp_subarray
            dev_info = self.component.get_device(dev_name)
            if dev_info is not None:
                dev_info.resources = assign_resources
                dev_info.last_event_arrived = time.time()
                self.component._invoke_device_callback(dev_info)

    def is_already_assigned(self, dish_id: str) -> bool:
        """
        Check if a Dish is already assigned to a subarray

        :param dish_id: id of the dish
        :type dish_id: str

        :return True is already assigned, False otherwise
        """
        self.logger.debug(
            "Checking if dish with ID %s is already assigned", dish_id
        )
        for devInfo in self.devices:
            if isinstance(devInfo, SubArrayDeviceInfo):
                self.logger.debug(
                    "Subarray Device resources for device %s: %s",
                    devInfo.dev_name,
                    str(devInfo.resources),
                )
                if devInfo.resources is None:
                    return False
                if dish_id in devInfo.resources:
                    return True
        return False

    def get_telescope_health_state(self) -> HealthState:
        """Getter method for telescope health state"""
        return self.component.telescope_health_state

    def get_telescope_availability(self) -> dict:
        """Getter method for Telescope Availability"""
        return self.component.telescope_availability

    def set_telescope_availability(self, telescope_availability) -> None:
        """Setter method for telescope availability"""
        self.component.telescope_availability = telescope_availability

    def _aggregate_state(self) -> None:
        """
        Aggregates both telescope state and tmc op state
        """
        self._aggregate_telescope_state()
        self._aggregate_tm_op_state()

    def get_telescope_state(self):
        """Getter method for telescope state"""
        return self.component.telescope_state

    def _aggregate_tm_op_state(self):
        """
        Aggregates TMC devices states
        """
        if self._op_state_aggregator is None:
            self._op_state_aggregator = TMCOpStateAggregator(self, self.logger)
        with self.lock:
            self.component.tmc_op_state = self._op_state_aggregator.aggregate()

    def get_tmc_op_state(self):
        """Getter method for TMC Op State Model"""
        return self.component.tmc_op_state

    # TODO: Kept it for reference. Not getting called anywhere.
    def _update_resources(self, subarray_dev_info: DeviceInfo) -> None:
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

    def _update_imaging(self) -> None:
        """
        Checks if CSP is ON and if atleast one Dish is ON. If both
        the conditions are true,
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

    def telescope_on(
        self,
        task_callback: TaskCallbackType | None = None,
        task_abort_event=None,
    ):
        """
        Turn the Telescope On.

        :return: a result code and message
        """
        telescope_on_command_object = TelescopeOn(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        return telescope_on_command_object.telescope_on(
            logger=self.logger,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def telescope_off(
        self, task_callback: Callable = None, task_abort_event=None
    ):
        """
        Turn the Telescope Off.

        :return: a result code and message
        """
        telescope_off_command_object = TelescopeOff(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        return telescope_off_command_object.telescope_off(
            logger=self.logger,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def telescope_standby(
        self, task_callback: Callable = None, task_abort_event=None
    ):
        """
        Standby the Telescope.

        :return: a result code and message
        """
        telescopestandby_command_object = TelescopeStandby(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        return telescopestandby_command_object.telescope_standby(
            logger=self.logger,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def is_input_json_valid(self, argin: str) -> Tuple[bool, str]:
        """
        Checks inputs json.

        param argin: input json string
        :type argin: str
        """
        try:
            json_argument = json.loads(argin)
            self.logger.debug("JSON argin is in correct format.")
            return True, json_argument
        except json.JSONDecodeError as e:
            return False, f"Problem in loading the JSON string: {e}"

    def check_subarray_id_in_json(
        self, json_argument: str
    ) -> Tuple[bool, str]:
        """
        Checks subarray id is present in json or not.

        Args:
            json_argument (str): input json string

        Returns:
            Tuple(bool, str):

        """
        try:
            subarray_id = json_argument["subarray_id"]
            return True, subarray_id
        except Exception as e:
            exp = "subarray_id key is not present in the input json argument"
            return (
                False,
                (f"{exp}:{e}"),
            )

    def get_subarray_id(self, argin: str) -> int:
        """Provides subarray id from assign json.

        :param argin: Assign json string
        :type argin: str
        :return: returns subarray id
        :rtype: _type_
        """
        return json.loads(argin).get("subarray_id")

    def get_command_id(self, unique_id):
        """
        Returns the command id mapped to the given unique_id.

        Args:
            unique_id: unique id of the command

        Returns:
            str: command id corresponding to unique_id
        """
        for cmd_id, uids in self.command_mapping.items():
            if unique_id in uids:
                return cmd_id
        return None

    def command_not_allowed_callable(
        self,
        subarray_id: int = 0,
        desired_obsstate: List | None = None,
        command_name: str = "",
    ):
        """This method provides callable for command not allowed

        Args:
            subarray_id (int): subarray_id
            desired_obsstate (List): desired observation state
            command_name (str): command name

        """

        def is_subarray_in_right_obs_state() -> bool:
            """
            Checks subarray obsstate before invoking command

            :param subarray_id: subarray id on which command invoke
            :type subarray_id: int
            :param desired_obsstate: list of obs states which are allowed
            :type desired_obsstate: List
            :param command_name: name of command for obstate check
            :type: str

            :return: return boolean value if command in valid obstate else
                return exception.
            """
            self.check_device_responsiveness_command(command_name, subarray_id)
            if subarray_id and desired_obsstate:
                subarray_devices = self.input_parameter.subarray_dev_names
                for device in subarray_devices:
                    subarray_device_id = re.findall(r"\d+", device)
                    if subarray_id == int(subarray_device_id[0]):
                        subarray_obstate = self.get_device(device).obs_state
                        if subarray_obstate not in desired_obsstate:
                            raise StateModelError(
                                f"{command_name} command not permitted "
                                + f"in observation state {subarray_obstate}"
                            )
            return True

        return is_subarray_in_right_obs_state

    def is_command_allowed_before_lrc_start(
        self,
        subarray_id: int = 0,
        command_name: str = "",
    ):
        """This method checks if command is allowed before LRC start

        Args:
            subarray_id (int): subarray_id
            command_name (str): command name

        Returns:
            boolean value if command in valid obstate else
            return exception.

        Raises:
            StateModelError: If command not permitted in observation state
            SubarrayNotPresentError: If subarray not available
            CommandNotAllowed: If command not allowed due to other
                unavailable devices

        """

        self.check_device_responsiveness_command(command_name, subarray_id)
        allowed_obs_states = {
            "AssignResources": [ObsState.EMPTY, ObsState.IDLE],
            "ReleaseResources": [ObsState.IDLE],
        }
        if command_name in allowed_obs_states:
            desired_obsstate = allowed_obs_states.get(command_name)
        else:
            desired_obsstate = None
        if subarray_id and desired_obsstate:
            subarray_devices = self.input_parameter.subarray_dev_names
            for device in subarray_devices:
                subarray_device_id = re.findall(r"\d+", device)
                if subarray_id == int(subarray_device_id[0]):
                    subarray_obstate = self.get_device(device).obs_state
                    if subarray_obstate not in desired_obsstate:
                        raise StateModelError(
                            f"{command_name} command not permitted "
                            + f"in observation state {subarray_obstate}"
                        )
        return True

    def check_device_responsiveness_command(
        self, command_name: str, subarray_id: int
    ) -> None:
        """
        Override this method to add responsive checks for the devices

        Args:
            command_name (str): Command name for the check
            subarray_id (int): Subarray id

        """
        if command_name in self.supported_commands_for_responsive_check:
            self.logger.debug("Checking the devices for: %s", command_name)
            if subarray_id:
                # check for the availability of specific subarray
                self.check_if_subarray_is_responsive(subarray_id)
            else:
                self.check_if_subarrays_are_responsive()

    def validate_subarray_id(self, json_argument: dict):
        """Validates the subarray id in the assign resources json.

        :param json_argument: Assign Resources json.
        :type json_argument: dict
        :raises InvalidJSONError: Raises error if subarray_id is not present.
        """
        if not json_argument.get("subarray_id"):
            raise InvalidJSONError(
                "subarray_id key is not present in the input json argument"
            )

    def log_state(self, msg: str = "Device States") -> None:
        """Log state method for"""
        device_names = []
        dev_states = []

        for device in self.devices:
            device_names.append(device.dev_name)
            dev_states.append(device.state)

        device_states = pd.DataFrame(
            {"Devices": device_names, "STATE": dev_states}
        )
        self.logger.info("\n" + msg + "\n" + device_states.to_string() + "\n")

    def get_adapter_by_device_name(self, device_name: str):
        """
        The get_adapter_by_device_name method takes a device_name as
        input and searches for an adapter object in the adapter_factory
        object's adapters attribute that matches the input device_name.
        If a matching adapter object is found, it is returned. If no
        matching adapter object is found, first adapter is returned.

        Args:
            device_name (str): The name of the device to search for.

        Returns:
            An adapter object if a matching device is found,
            otherwise first adapter object is returned.

        """
        if not self.adapter_factory.adapters:
            return None
        for adapter in self.adapter_factory.adapters:
            if adapter.dev_name == device_name:
                return adapter
        return self.adapter_factory.adapters[0]

    def get_sdp_controller_admin_mode(self) -> AdminMode:
        """
        Retrieve the adminMode of sdp controller.

        Returns:
            This method returns the adminMode of the
            TMC sdp controller leaf Node.
        """
        sdp_mln_adapter = self.adapter_factory.get_or_create_adapter(
            self.get_sdp_master_leaf_node_dev_name(),
            adapter_type=AdapterType.SDP_MASTER_LEAF_NODE,
        )
        return sdp_mln_adapter.sdpControllerAdminMode

    def get_csp_controller_admin_mode(self) -> AdminMode:
        """
        Retrieve the adminMode of CSP controller.

        Returns:
            str: The adminMode of the TMC CSP controller Leaf Node.
        """
        csp_mln_adapter = self.adapter_factory.get_or_create_adapter(
            self.get_csp_master_leaf_node_dev_name(),
            adapter_type=AdapterType.CSP_MASTER_LEAF_NODE,
        )
        return csp_mln_adapter.cspControllerAdminMode

    def get_mccs_controller_admin_mode(self) -> AdminMode:
        """
        Retrieve the adminMode of mccs controller.

        Returns:
            This method returns the adminMode of the
            TMC mccs controller leaf Node.

        """
        mccs_mln_adapter = self.adapter_factory.get_or_create_adapter(
            self.get_mccs_master_leaf_node_dev_name(),
            adapter_type=AdapterType.MCCS_MASTER_LEAF_NODE,
        )
        return mccs_mln_adapter.mccsControllerAdminMode

    def is_command_allowed(self):
        """This method needs to be overridden by the child classes
        in order to check whether command is allowed or not"""

    def off(
        self, task_callback: TaskCallbackType | None = None
    ) -> tuple[TaskStatus, str]:
        """This method needs to be overridden by the child classes
        in order to check have functionality under off command"""
        message = (
            "Command is not Implemented in Central Node."
            + " Please use TelescopeOff command"
        )
        return TaskStatus.REJECTED, message

    def on(
        self, task_callback: TaskCallbackType | None = None
    ) -> tuple[TaskStatus, str]:
        """This method needs to be overridden by the child classes
        in order to check have functionality under off command"""
        message = (
            "Command is not Implemented in Central Node."
            + " Please use TelescopeOn command"
        )
        return TaskStatus.REJECTED, message

    def start_communicating(self):
        """This method needs to be overridden by the child classes
        to have this functionality"""

    def stop_communicating(self):
        """This method needs to be overridden by the child classes
        to have this functionality"""

    def standby(
        self, task_callback: TaskCallbackType | None = None
    ) -> tuple[TaskStatus, str]:
        """This method needs to be overridden by the child classes
        in order to check have functionality under off command"""
        message = (
            "Command is not Implemented in Central Node."
            + " Please use TelescopeStandby command"
        )
        return TaskStatus.REJECTED, message

    def _aggregate_telescope_state(self):
        """
        Aggregates telescope state
        """

    def check_availability_for_release(self, argin: str):
        """Checks the subarray availability before release based on id
        present in the json.

        :param argin: release resource input json.
        :type argin: str
        :raises Exception: Raises Exception if subarray is not available.
        """
        subarray_id = self.get_subarray_id(argin)
        subarray = self.subarray_trl_prefix + str(subarray_id).zfill(2)
        telescope_availability = self.get_telescope_availability()
        subarray_availability = telescope_availability.get(subarray)
        if subarray_availability is False:
            raise Exception(f"Subarray {subarray} is not available.")

"""
This module provided an implementation of the Central Node ComponentManager.
"""

from __future__ import annotations

import json
import threading
import time
from multiprocessing import Event
from multiprocessing import Lock as ProcessLock
from multiprocessing import Manager
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
from ska_control_model import HealthState, TaskStatus
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.control_model import ObsState
from ska_tango_base.software_bus import SharingObserver, Signal
from ska_tmc_common import (
    AdapterFactory,
    Aggregator,
    DeviceInfo,
    DishDeviceInfo,
    InvalidJSONError,
    SubArrayDeviceInfo,
)
from ska_tmc_common.v2.tmc_component_manager import TmcComponentManager
from tango.utils import PyTangoThread

from ska_tmc_centralnode.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
)
from ska_tmc_centralnode.manager.aggregators import TMCOpStateAggregator
from ska_tmc_centralnode.manager.component_manager_config import (
    CentralNodeComponentManagerConfig,
)
from ska_tmc_centralnode.manager.event_data_manager import EventDataManager
from ska_tmc_centralnode.manager.event_manager import CentralNodeEventManager
from ska_tmc_centralnode.manager.event_processor import EventProcessor
from ska_tmc_centralnode.model.component import (
    CentralComponent,
    MCCSDeviceInfo,
)
from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)

from .aggregators import (
    TelescopeStateAggregatorLow,
    TelescopeStateAggregatorMid,
)
from .device_attribute_map_builder import DeviceAttributeMapBuilder
from .event_callback_manager.event_callback_manager import EventCallbackManager


class CNComponentManager(SharingObserver, TmcComponentManager):
    """
    A component manager for The Central Node component.

    It supports:

    1. Monitoring its component, e.g. detect that it has been turned off
    or on\n

    2. Receiving the change events from lower level devices and trigger
    the TMC and telescope state aggregation
    """

    _array_layout_url: Signal = Signal[dict](stored=True)
    _default_array_layout_url: Signal = Signal[dict](stored=True)

    # pylint:disable=keyword-arg-before-vararg
    def __init__(self, config: CentralNodeComponentManagerConfig):
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
        super().__init__(
            config.input_parameter,
            config.logger,
            _component=config.component,
            _liveliness_probe=config.liveliness_probe_type,
            _event_manager=False,
            proxy_timeout=config.proxy_timeout,
            event_subscription_check_period=(
                config.event_subscription_check_period
            ),
            liveliness_check_period=config.liveliness_check_period,
        )
        self.config = config
        self.logger = config.logger
        self.component = config.component or CentralComponent(config.logger)
        self.event_manager = self.config.event_manager_enabled
        self.input_parameter = self.config.input_parameter
        self.adapter_factory = AdapterFactory()
        self.event_data_manager = EventDataManager(self)
        self.process_lock = ProcessLock()
        self._telescope_state_aggregator: Optional[
            Union[TelescopeStateAggregatorLow, TelescopeStateAggregatorMid]
        ] = None
        self._health_state_aggregator = None
        self.op_state_aggregator = None
        self.command_in_progress: str = ""
        self.command_mapping: Dict[str, str | list[dict]] = {}
        self.rlock = threading.RLock()
        self._telescope_availability_aggregator = Aggregator(
            self, logger=config.logger
        )
        self._stop_thread: threading.Event = threading.Event()
        self._liveliness_probe = None
        self.event_processor: EventProcessor = EventProcessor(
            stop_event=self._stop_thread,
            logger=config.logger,
            on_error=self.update_event_failure,
        )
        self.aggregate_process_manager = Manager()
        self.event_data_queue = self.aggregate_process_manager.Queue()
        self.aggregated_health_state = self.aggregate_process_manager.list(
            [""]
        )
        self.aggregate_value_update_event = Event()
        self.aggregate_process_monitor_thread = PyTangoThread(
            target=self.aggregate_process_monitor
        )
        self.aggregate_process_monitor_thread.start()
        self.event_manager_object: CentralNodeEventManager = (
            CentralNodeEventManager(self, logger=config.logger)
        )
        self.command_completion_cond = threading.Condition()
        self._event_cb_manager = EventCallbackManager(
            logger=self.logger,
            component=self.component,
            command_completion_cond=self.command_completion_cond,
            input_parameter=self.input_parameter,
            event_data_manager=self.event_data_manager,
            _aggregate_state=self._aggregate_state,
        )

    def on_new_shared_bus(self) -> None:
        super().on_new_shared_bus()
        self._array_layout_url = {}
        self._default_array_layout_url: dict = (
            self.config.array_layout_config.default_url
        )

    def _get_event_handlers(self) -> dict:
        """Returns event handlers.

        :return: Dictionary with attribute name and its event handler.
        :rtype: dict
        """
        return {
            "obsState": self._event_cb_manager.update_device_obs_state,
            "assignedResources": (
                self._event_cb_manager.update_device_assigned_resource
            ),
            "healthState": self._event_cb_manager.update_device_health_state,
            "adminMode": self._event_cb_manager.update_device_admin_mode,
        }

    def _register_event_handlers(self, event_handlers: dict) -> None:
        """Registers event processing methods
        :param event_handlers: Dictionary with attribute name and its
        event handler.
        """
        for attr, method in event_handlers.items():
            self.event_processor.register_handler(attr, method)

    def setup_event_subscription(self) -> None:
        """
        Sets up the event subscription after input parameters are updated.
        """
        _device_attr_map_builder = DeviceAttributeMapBuilder(
            self.logger, self.input_parameter
        )
        self.start_event_manager(
            _device_attr_map_builder.build(self.devices), timeout=1000
        )
        if self.config.event_manager_enabled:
            self.event_manager_object.init_timeout(self.event_thread_id)
        self.logger.debug("Successfully subscribed the events")

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

    def aggregate_process_monitor(self):
        """This method keep tracking aggregate health state changed
        from aggregation process
        """
        while not self._stop_thread.is_set():
            if self.aggregate_value_update_event.wait(0.3):
                self.aggregate_value_update_event.clear()
                current_health_state = self.aggregated_health_state[0]
                if current_health_state is not None:
                    self.component.telescope_health_state = (
                        current_health_state
                    )
                    self.logger.debug(
                        "Aggregate telescope health state called %s",
                        str(current_health_state),
                    )

        self.logger.debug("aggregation process monitor thread stopped")

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
            self.logger.debug("Aggregation process stopped")

    def __del__(self):
        """shutdown aggregation process"""
        self.logger.debug("Component destructor called")
        self.stop_all_process()
        self.stop()

    def cleanup(self):
        self.stop_all_process()
        self.stop()

    def stop_event_manager(self) -> None:
        """Stops the Event Receiver"""
        if self.config.event_manager_enabled:
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
        self._stop_thread.set()

    def update_input_parameter(self) -> None:
        """updates the input parameter for component manager instance"""
        with self.lock:
            self.input_parameter.update(self)

    def reset(
        self: CNComponentManager, _task_callback: Optional[Callable] = None
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
        self.op_state_aggregator = _op_state_aggregator

    @property
    def devices(self):
        """
        Return the list of the monitored devices

        :return: list of the monitored devices
        """
        return self.component.devices

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
        if (
            not telescope_availability.get("csp_master_leaf_node", False)
            is True
        ):
            self.logger.debug(
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
        if (
            not telescope_availability.get("sdp_master_leaf_node", False)
            is True
        ):
            self.logger.debug(
                "SdpMasterLeafNode is not available to receive command"
            )
            return False

        return True

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
            dev_info = SubArrayDeviceInfo(device_name, False)
        elif (
            isinstance(self.input_parameter, InputParameterMid)
            and device_name in self.get_dish_leaf_node_device_names()
        ):
            dev_info = DishDeviceInfo(device_name, False)
        elif (
            isinstance(self.input_parameter, InputParameterLow)
            and device_name.lower()
            in self.get_mccs_master_leaf_node_dev_name()
        ):
            dev_info = MCCSDeviceInfo(device_name, False)
        else:
            dev_info = DeviceInfo(device_name, False)
        self.component.update_device(dev_info)
        if self.liveliness_probe_object:
            self.liveliness_probe_object.add_device(device_name)

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
            dev_info = self.get_device(device_name)
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
            dev_info = self.get_device(device_name)
            dev_info.last_event_arrived = time.time()
            self.component.last_device_info_changed = dev_info

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
        for dev_info in self.devices:
            if isinstance(dev_info, SubArrayDeviceInfo):
                self.logger.debug(
                    "Subarray Device resources for device %s: %s",
                    dev_info.dev_name,
                    str(dev_info.resources),
                )
                if dev_info.resources is None:
                    return False
                if dish_id in dev_info.resources:
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
        if self.op_state_aggregator is None:
            self.op_state_aggregator = TMCOpStateAggregator(self, self.logger)
        with self.lock:
            self.component.tmc_op_state = self.op_state_aggregator.aggregate()

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

    def telescope_on(
        self,
        task_callback: TaskCallbackType,
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
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def telescope_off(
        self, task_callback: TaskCallbackType, task_abort_event=None
    ):
        """
        Turn the Telescope Off.

        :return: a result code and message
        """
        telescope_off_command_object = TelescopeOff(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        return telescope_off_command_object.telescope_off(
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def telescope_standby(
        self, task_callback: TaskCallbackType, task_abort_event=None
    ):
        """
        Standby the Telescope.

        :return: a result code and message
        """
        telescopestandby_command_object = TelescopeStandby(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        return telescopestandby_command_object.telescope_standby(
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
        self, json_argument: dict
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

    def get_command_id(self, unique_id) -> Union[str, None]:
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

    def validate_subarray_id(self, json_argument: dict) -> None:
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
        self.logger.debug(
            "%s\n%s",
            msg,
            device_states.to_string(),
        )

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

    def check_availability_for_release(self, argin: str) -> None:
        """Checks the subarray availability before release based on id
        present in the json.

        :param argin: release resource input json.
        :type argin: str
        :raises Exception: Raises Exception if subarray is not available.
        """
        subarray_id = self.get_subarray_id(argin)
        subarray = self.config.subarray_trl_prefix + str(subarray_id).zfill(2)
        telescope_availability = self.get_telescope_availability()
        subarray_availability = telescope_availability.get(subarray)
        if subarray_availability is False:
            raise Exception(f"Subarray {subarray} is not available.")

    def _publish_signal(self, name: str, value: Any) -> None:
        """Publish a software-bus signal while
        tolerating missing bus wiring."""
        try:
            setattr(self, name, value)
        except RuntimeError:
            # Component managers used without shared bus in tests.
            pass

    def is_command_allowed(self, command_name: str = "") -> bool:
        """Check whether the given command is allowed

        :param command_name: command name
        :type command_name: str
        :return: Returns True if command is allowed.
        :rtype: bool
        """
        if hasattr(self, "cmd_allowed_validator"):
            return self.cmd_allowed_validator.is_command_allowed(command_name)
        return False

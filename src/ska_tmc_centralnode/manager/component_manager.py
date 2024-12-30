"""
This module provided an implementation of the Central Node ComponentManager.
"""
from __future__ import annotations

import json
import re
import threading
import time
from queue import Empty, Queue
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import tango
from ska_control_model import HealthState
from ska_ser_skuid.client import SkuidClient
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tango_base.faults import StateModelError
from ska_telmodel.schema import validate
from ska_tmc_common import (
    AdapterFactory,
    Aggregator,
    CommandNotAllowed,
    DeviceInfo,
    DishDeviceInfo,
    InvalidJSONError,
    InvalidReceptorIdError,
    LivelinessProbeType,
    LRCRCallback,
    ResourceNotPresentError,
    SubArrayDeviceInfo,
    SubarrayNotPresentError,
    TmcComponentManager,
)
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode.commands.release_resources_command import (
    ReleaseResources,
)
from ska_tmc_centralnode.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode.commands.telescope_standby_command import (
    TelescopeStandby,
)
from ska_tmc_centralnode.input_validator import (
    AssignResourceValidator,
    ReleaseResourceValidator,
)
from ska_tmc_centralnode.manager.aggregators import TMCOpStateAggregator
from ska_tmc_centralnode.manager.event_receiver import CentralNodeEventReceiver
from ska_tmc_centralnode.model.component import (
    CentralComponent,
    MCCSDeviceInfo,
)
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

    # pylint:disable=keyword-arg-before-vararg
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
        _telescope_availability_callback=None,
        component_state_callback=None,
        proxy_timeout=500,
        sleep_time=1,
        skuid_service=(
            "ska-ser-skuid-test-svc.ska-tmc-centralnode.svc.techops.internal"
            + ".skao.int:9870"
        ),
        command_timeout=30,
        assignresources_interface: str = "",
        releaseresources_interface: str = "",
        *args,
        **kwargs,
    ):
        """
        Initialise a new ComponentManager instance.

        :param op_state_model: the operational state model used
          by this component
            manager
        :param _input_parameter: allows to specify InputParameter
          class for TMC Mid or Low
        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        :param _liveliness_probe: allows to enable/disable
          LivelinessProbe usage
        :param _event_receiver: allows to enable/disable
          EventReceiver usage
        """

        self._component = _component or CentralComponent(logger)

        super().__init__(
            _input_parameter,
            logger,
            _component=self._component,
            _liveliness_probe=_liveliness_probe,
            _event_receiver=False,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            proxy_timeout=proxy_timeout,
            sleep_time=sleep_time,
            *args,
            **kwargs,
        )
        self.op_state_model = op_state_model
        self.adapter_factory = AdapterFactory()
        self.event_receiver = True
        self.command_timeout = command_timeout
        self.assignresources_interface = assignresources_interface
        self.releaseresources_interface = releaseresources_interface

        self.event_receiver = _event_receiver
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
            _telescope_availability_callback,
        )
        self._telescope_state_aggregator = None
        self._health_state_aggregator = None
        self._op_state_aggregator = None
        self.skuid_service = skuid_service
        self.long_running_result_callback = LRCRCallback(self.logger)
        self.command_in_progress: str = ""
        self.subarray_devname: str = ""
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
        self._liveliness_probe = None
        self.supported_commands_for_responsive_check = [
            "TelescopeOn",
            "TelescopeOff",
            "TelescopeStandby",
            "AssignResources",
            "ReleaseResources",
        ]
        self.event_queues: Dict[str, Queue] = {
            "obsState": Queue(),
            "assignedResources": Queue(),
            "healthState": Queue(),
        }

        self.event_processing_methods: Dict[
            str, Callable[[str, Any], None]
        ] = {
            "obsState": self.update_device_obs_state,
            "assignedResources": self.update_device_assigned_resource,
            "healthState": self.update_device_health_state,
        }

    def _start_event_processing_threads(self) -> None:
        """Start all the event processing threads."""
        for attribute in self.event_queues:
            thread = threading.Thread(
                target=self.process_event, args=[attribute], name=attribute
            )
            thread.start()

    def process_event(self, attribute_name: str) -> None:
        """Process the given attribute's event using the data from the
        event_queues and invoke corresponding process method.

        :param attribute_name: Name of the attribute for which event is to be
            processed
        :type attribute_name: str

        :returns: None
        """
        while True:
            try:
                self.logger.info("%s", list(self.event_queues[attribute_name]))
                event_data = self.event_queues[attribute_name].get(
                    block=True, timeout=0.1
                )
                if not self.check_event_error(
                    event_data, f"{attribute_name}_Callback"
                ):
                    if attribute_name == "loadDishConfigResultAsync":
                        self.event_processing_methods[attribute_name](
                            event_data.device.dev_name(),
                            event_data.argout,
                        )
                    else:
                        self.event_processing_methods[attribute_name](
                            event_data.device.dev_name(),
                            event_data.attr_value.value,
                        )
            except Empty:
                # If an empty exception is raised by the Queue, we can
                # safely ignore it.
                pass
            except Exception as exception:
                self.logger.error(exception)

    def check_event_error(self, event: tango.EventData, callback: str):
        """Method for checking event error."""
        if event.err:
            error = event.errors[0]
            self.logger.error(
                "Error occurred on %s for device: %s - %s, %s",
                callback,
                event.device.dev_name(),
                error.reason,
                error.desc,
            )
            self.update_event_failure(event.device.dev_name())
            return True
        return False

    def stop_event_receiver(self):
        """Stops the event receiver."""
        if self.event_receiver:
            self.event_receiver_object.stop()

    def reset(
        self: CNComponentManager, task_callback: Optional[Callable] = None
    ) -> tuple[TaskStatus, str]:
        """
        Placeholder method for reset command.
        :param task_callback: Update task status, defaults to None
        :type task_callback: Callable, optional
        :return: task_status, message
        :rtype: tuple
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

    def stop(self) -> None:
        """stops liveliness probe"""
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

    # pylint:disable =inconsistent-return-statements
    def get_subarray_obsstate(self) -> ObsState:
        """
        Get Current device obsState

        :return: current obsstate
        :rtype: ObsState
        """
        if self.subarray_devname:
            return self.get_device(self.subarray_devname).obs_state

        # return self.get_device(self.subarray_devname).obs_state

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
        """Checks if subarray are responsive"""
        self.logger.info("Checking if subarrays are responsive")
        return self._check_if_device_is_responsive(
            self.input_parameter.subarray_dev_names
        )

    def _check_if_device_is_responsive(self, dev_names: List[str]):
        """checks if the device is responsive"""
        count = 0
        for dev_name in dev_names:
            dev_info = self.get_device(dev_name)
            if dev_info is not None and not dev_info.unresponsive:
                self.logger.debug(
                    f"Device {dev_name} dev_info.unresponsive:"
                    + f" {dev_info.unresponsive} "
                )
                count += 1
        if count == 0:
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
        :param dev_name: device name
        :type dev_name: str
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

        :param dev_name: name of the device
        :type dev_name: str
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

        :param device_info: Information about the device
        :type device_info: DeviceInfo
        :param exception: Exception raised during the ping failure
        :type exception: Exception
        """
        # Log the device failure with the device name
        message = (
            f"device: {device_info.dev_name}: {exception}"
            + "failed to respond"
        )
        self.logger.error(message)

        with self.rlock:
            device_name = device_info.dev_name
            dev_info = self.component.get_device(device_name)
            # Update the device status with the exception details
            dev_info.update_unresponsive(True, str(exception))
            # Aggregate the telescope availability data
            self._telescope_availability_aggregator.aggregate()

    def update_event_failure(self, device_name: str) -> None:
        """updates event failures in Dev info"""
        with self.rlock:
            devInfo = self.component.get_device(device_name)
            devInfo.last_event_arrived = time.time()
            devInfo.update_unresponsive(False)
            self.component._invoke_device_callback(devInfo)

    def update_device_health_state(
        self, device_name: str, health_state: HealthState
    ) -> None:
        """
        Update a monitored device health state
        aggregate the health states available

        :param dev_name: name of the device
        :type dev_name: str
        :param health_state: health state of the device
        :type health_state: HealthState
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
                devInfo.update_unresponsive(False)
                self.component._invoke_device_callback(devInfo)

        self._aggregate_health_state()

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
                devInfo.last_event_arrived = time.time()
                devInfo.update_unresponsive(False)
                self.component._invoke_device_callback(devInfo)
            self.observable.notify_observers(attribute_value_change=True)

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
            self.logger.info(
                "Updating assigned resources for device '%s': %s",
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
                dev_info.update_unresponsive(False)
                self.component._invoke_device_callback(dev_info)

    def is_already_assigned(self, dish_id: str) -> bool:
        """
        Check if a Dish is already assigned to a subarray

        :param dish_id: id of the dish
        :type dish_id: str

        :return True is already assigned, False otherwise
        """
        self.logger.debug(
            "Checking if dish with ID '%s' is already assigned", dish_id
        )
        for devInfo in self.devices:
            if isinstance(devInfo, SubArrayDeviceInfo):
                self.logger.debug(
                    "Subarray Device resources for device '%s': %s",
                )
                if devInfo.resources is None:
                    return False
                if dish_id in devInfo.resources:
                    return True
        return False

    def get_telescope_health_state(self) -> HealthState:
        """Getter method for telescope health state"""
        return self.component.telescope_health_state

    def get_telescope_availability(self) -> bool:
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

    def telescope_on(self, task_callback: TaskCallbackType | None = None):
        """
        Turn the Telescope On.

        :return: a result code and message
        """
        telescope_on_command = TelescopeOn(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        task_status, response = self.submit_task(
            telescope_on_command.telescope_on,
            args=[self.logger],
            task_callback=task_callback,
            is_cmd_allowed=self.command_not_allowed_callable(
                command_name="TelescopeOn"
            ),
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
            is_cmd_allowed=self.command_not_allowed_callable(
                command_name="TelescopeOff"
            ),
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
            is_cmd_allowed=self.command_not_allowed_callable(
                command_name="TelescopeStandby"
            ),
        )
        return task_status, response

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

        param json_argument: input json string
        :type json_argument: str
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
            self.check_device_responsiveness(command_name)
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

    def check_device_responsiveness(self, command_name: str) -> None:
        """
        Override this method to add responsive checks for the devices
        :param command_name: Command name for the check
        :type command_name: str
        """
        return True

    def assign_resources(
        self, argin: str, task_callback: Optional[Callable] = None
    ):
        """
        Submit the AssignResources command in queue.

        :param argin: input json string for assign resource command
        :type argin: str
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :return: task_status
        :rtype: tuple
        """

        is_json_valid, input_json_or_message = self.is_input_json_valid(argin)
        if not is_json_valid:
            return TaskStatus.REJECTED, input_json_or_message

        result, subarray_id_or_message = self.check_subarray_id_in_json(
            input_json_or_message
        )
        if not result:
            return TaskStatus.REJECTED, subarray_id_or_message

        # Execute the command if the input JSON is valid
        self.logger.info("Calling component manager assign_resources method")
        assign_resources_command = AssignResources(
            self,
            adapter_factory=self.adapter_factory,
            skuid=SkuidClient(self.skuid_service),
            logger=self.logger,
        )

        if isinstance(self.input_parameter, InputParameterLow):
            try:
                validate(
                    version=self.assignresources_interface,
                    config=json.loads(argin),
                    strictness=2,
                )
            except Exception as exception:
                # Catch other unexpected exceptions
                self.logger.exception(
                    "Exception occurred while validating for "
                    + "assignresource json : %s ",
                    exception,
                )
                return assign_resources_command.reject_command(str(exception))

        elif isinstance(self.input_parameter, InputParameterMid):
            # Utilize CDM to validate json.
            available_subarrays_list = self.input_parameter.subarray_dev_names
            dish_leaf_node_prefix = self.input_parameter.dish_leaf_node_prefix
            available_dish_leaf_node_devices = (
                self.input_parameter.dish_leaf_node_dev_names
            )
            try:
                assign_validator = AssignResourceValidator(
                    available_subarrays_list,
                    available_dish_leaf_node_devices,
                    dish_leaf_node_prefix,
                    self.logger,
                )

                json_argument = assign_validator.loads(argin)

            except (
                InvalidJSONError,
                SubarrayNotPresentError,
                ResourceNotPresentError,
                ValueError,
                InvalidReceptorIdError,
            ) as e:
                return assign_resources_command.reject_command(str(e))

        # Reject command if Subarray is not available
        json_argument = json.loads(argin)
        subarray_id = json_argument["subarray_id"]
        subarray_suffics = "/" + str(subarray_id)
        subarrays_list = list(
            self._component.telescope_availability["tmc_subarrays"].keys()
        )
        for subarray in subarrays_list:
            telescope_availability = self.get_telescope_availability()
            self.logger.debug(
                f"Telescope availability is: {telescope_availability}"
            )
            self.logger.debug(f"subarrays_list is: {subarrays_list}")
            if (
                subarray.endswith(subarray_suffics)
                and telescope_availability["tmc_subarrays"][subarray] is False
            ):
                return assign_resources_command.reject_command(
                    f"Subarray {subarray} is not available."
                )

        # validate processing block
        (
            is_processing_block_present,
            processing_block_error_msg,
        ) = assign_resources_command._validate_and_update_resource_config(
            json_argument
        )
        if not is_processing_block_present:
            return assign_resources_command.reject_command(
                processing_block_error_msg
            )

        task_status, response = self.submit_task(
            assign_resources_command.assign_resources,
            kwargs={"argin": json.dumps(json_argument)},
            task_callback=task_callback,
            is_cmd_allowed=self.command_not_allowed_callable(
                subarray_id_or_message,
                [ObsState.EMPTY, ObsState.IDLE],
                "AssignResources",
            ),
        )
        self.logger.info(
            "AssignResources command's status: "
            + f"{task_status.name}, and response: {response}"
        )

        return task_status, response

    def release_resources(
        self, argin: str, task_callback: Optional[Callable] = None
    ):
        """
        Submit the ReleaseResource command in queue.

        :param argin: input json string for release resource command
        :type argin: str
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :return: task_status
        :rtype: tuple
        """
        is_json_valid, input_json_or_message = self.is_input_json_valid(argin)
        if not is_json_valid:
            return TaskStatus.REJECTED, input_json_or_message

        result, subarray_id_or_message = self.check_subarray_id_in_json(
            input_json_or_message
        )
        if not result:
            return TaskStatus.REJECTED, subarray_id_or_message

        release_resources_command = ReleaseResources(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        # Execute the command if the input JSON is valid
        if isinstance(self.input_parameter, InputParameterLow):
            try:
                validate(
                    version=self.releaseresources_interface,
                    config=json.loads(argin),
                    strictness=2,
                )
            except Exception as e:
                return release_resources_command.reject_command(str(e))
        elif isinstance(self.input_parameter, InputParameterMid):
            self.logger.info(f"Json argument::{input_json_or_message}")
            # Utilize CDM to validate json.
            try:
                release_validator = ReleaseResourceValidator(self.logger)
                input_json_or_message = release_validator.loads(argin)
            except InvalidJSONError as e:
                return release_resources_command.reject_command(str(e))

        # Reject command if Subarray is not available
        subarray_id = subarray_id_or_message
        subarray_suffics = "/" + str(subarray_id)
        subarrays_list = list(
            self._component.telescope_availability["tmc_subarrays"].keys()
        )
        for subarray in subarrays_list:
            telescope_availability = self.get_telescope_availability()
            if (
                subarray.endswith(subarray_suffics)
                and telescope_availability["tmc_subarrays"][subarray] is False
            ):
                return release_resources_command.reject_command(
                    f"Subarray {subarray} is not available."
                )

        task_status, response = self.submit_task(
            release_resources_command.release_resources,
            kwargs={"argin": json.dumps(input_json_or_message)},
            task_callback=task_callback,
            is_cmd_allowed=self.command_not_allowed_callable(
                subarray_id_or_message, [ObsState.IDLE], "ReleaseResources"
            ),
        )
        self.logger.info(
            "ReleaseResources command's status: "
            + f"{task_status.name}, and response: {response}"
        )

        return task_status, response

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

    def _aggregate_health_state(self):
        """
        Aggregates all health states
        and call the relative callback if available
        """

    def _aggregate_telescope_state(self):
        """
        Aggregates telescope state
        """

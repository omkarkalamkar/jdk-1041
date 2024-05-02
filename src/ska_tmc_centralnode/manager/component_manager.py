"""
This module provided an implementation of the Central Node ComponentManager.
"""
from __future__ import annotations

import json
import re
import time
from typing import Callable, List, Optional, Tuple

import pandas as pd
from ska_control_model import HealthState
from ska_ser_skuid.client import SkuidClient
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tango_base.faults import StateModelError
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
from ska_tmc_centralnode.manager.aggregators import (
    LoadDishCfgCommandResultAggregator,
    TMCOpStateAggregator,
)
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
from ska_tmc_centralnode.utils.constants import (
    REQUIRED_LOW_ASSIGN_RESOURCE_KEYS,
    REQUIRED_LOW_RELEASE_RESOURCE_KEYS,
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
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
        skuid_service=(
            "ska-ser-skuid-test-svc.ska-tmc-centralnode.svc.techops.internal"
            + ".skao.int:9870"
        ),
        command_timeout=30,
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
            max_workers=max_workers,
            proxy_timeout=proxy_timeout,
            sleep_time=sleep_time,
            *args,
            **kwargs,
        )
        self.op_state_model = op_state_model
        self.adapter_factory = AdapterFactory()
        self.event_receiver = True
        self.command_timeout = command_timeout

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
        self.dev_names_for_load_dish_cfg = []
        self.no_of_events_for_command = 0
        self.load_dish_cfg_aggregated_result = None
        self.load_dish_cfg_command_id = None
        self.supported_commands = (
            "AssignResources",
            "ReleaseResources",
            "ReleaseAllResources",
        )
        self._telescope_availability_aggregator = Aggregator(
            self, logger=logger
        )
        self._liveliness_probe = None

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

    def get_load_disg_cfg_resultcode(self):
        """Return Aggregated command result for Load Dish Cfg command"""
        return self.load_dish_cfg_aggregated_result

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

    def check_if_mccs_mln_is_available(self) -> bool:
        """
        Returns boolean value based on availability of MccsMasterLeafNode,
        which indicated availability of Mccs Master.
        """
        telescope_availability = self.get_telescope_availability()
        if not telescope_availability["mccs_master_leaf_node"] is True:
            self.logger.info(
                "MccsMasterLeafNode is not available to receive command"
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
        self.liveliness_probe_object.add_device(device_name)

    def update_input_parameter(self) -> None:
        """updates the input parameter for component manager instance"""
        with self.lock:
            self.input_parameter.update(self)

    def update_ping_info(self, ping: int, device_name: str) -> None:
        """
        Update a device with correct ping information.

        :param dev_name: name of the device
        :type dev_name: str
        :param ping: device response time
        :type ping: int
        """
        with self.lock:
            dev_info = self.get_device(device_name)
            dev_info.ping = ping
            dev_info.update_unresponsive(False)
            self._telescope_availability_aggregator.aggregate()

    def update_device_ping_failure(
        self, device_info: DeviceInfo, exception: str
    ) -> None:
        """
        Set a device to failed and call the relative callback if available

        :param device_info: a device info
        :type device_info: DeviceInfo
        :param exception: an exception
        :type: Exception
        """
        self.logger.info(f"device failed: {device_info.dev_name}")
        self.logger.error(str(exception))
        with self.lock:
            self.component.update_device_exception(device_info, exception)
            self._telescope_availability_aggregator.aggregate()

    def update_event_failure(self, device_name: str) -> None:
        """updates event failures in Dev info"""
        with self.lock:
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
            self.logger.info(
                f"State evt callback for device {device_name}: {health_state}"
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
        with self.lock:
            self.logger.info(
                f"ObsState event callback for device {dev_name}: {obs_state}"
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
                devInfo.last_event_arrived = time.time()
                devInfo.update_unresponsive(False)
                self.component._invoke_device_callback(devInfo)

    def update_device_assigned_resource(
        self, dev_name: str, assign_resources: str
    ) -> None:
        """
        Update assign_resources for a monitored device

        :param dev_name: name of the device
        :type dev_name: str
        :param assign_resources: assign_resources
        :type assign_resources: str
        """
        with self.lock:
            self.logger.info(
                "assignedResources event callback for device %s : %s",
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
        self.logger.debug(f"Dish Id is: {dish_id}")
        for devInfo in self.devices:
            if isinstance(devInfo, SubArrayDeviceInfo):
                self.logger.debug(
                    f"Subarray Device resources: {devInfo.resources}"
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

    def update_load_dish_cfg_results(
        self, dev_name: str, value: tuple, is_async_result: bool = False
    ) -> None:
        """This method is used to update the result returned
        from Csp Master Leaf Node
        and returned from Dish Leaf Nodes for SetKValue command.
        Update result_codes_mapping with dev name as a key and
        command result as a value
        If all events are received from all device then aggregate
        the result
        Value contains (unique_id, ResultCode) or (unique_id,exception_msg)
        or (unique_id,TaskStatus)
        :param dev_name: name of the device who's event has been
        captured in this method
        :type dev_name: str
        :param value: longRunningCommandResult attribute event.
        :type value: tuple
        :param is_async_result: Whether this callback is called
        from Async command result call or
        longRunningCommandResult attribute callback
        Examples of value
        Async callback value: [array([0], dtype=int32), ['']]
        LongRunningCommandResultCallBack value:
        ('1698838234.9087641-LoadDishCfg',
        'Exception occurred, command failed.')
        """
        self.logger.info(
            "longRunningCommandResult event for device: %s, with value: %s",
            dev_name,
            value,
        )
        with self.lock:
            result_code_or_exception = []
            if is_async_result:
                # Set result code and message
                self.logger.debug(
                    "event from asynchronous command result callback %s",
                    value,
                )
                result_code_or_exception = [value[0][0], value[1][0]]

            else:
                unique_id, result_code_or_exception_or_task_status = value
                if unique_id.endswith("LoadDishCfg"):
                    if result_code_or_exception_or_task_status.isdigit():
                        # Failed event is called twice one with error message
                        # and other with result code
                        # in case of second Failed event just ignore
                        # it as Failed Message already updated in
                        # first event call
                        if dev_name not in self.result_codes_mapping:
                            result_code_or_exception = [
                                result_code_or_exception_or_task_status,
                                "",
                            ]
                    elif result_code_or_exception_or_task_status:
                        result_code_or_exception = [
                            ResultCode.FAILED,
                            result_code_or_exception_or_task_status,
                        ]
            if result_code_or_exception and self.dev_names_for_load_dish_cfg:
                self.result_codes_mapping[dev_name] = result_code_or_exception
                self.logger.info(
                    "Dev names for load_dish_cfg values %s "
                    + "and result_codes_mapping are %s",
                    self.dev_names_for_load_dish_cfg,
                    self.result_codes_mapping,
                )

            # When all events received from dishes and Csp master leaf node
            # then aggregate the result
            if len(self.dev_names_for_load_dish_cfg) == len(
                self.result_codes_mapping
            ):
                # Aggregate the result
                self.logger.info(
                    "All Events received for load dish cfg Aggregating results"
                )
                self.aggregate_load_dish_cfg_results()

    def aggregate_load_dish_cfg_results(self) -> None:
        """This method aggregate load dish cfg command result based on
        generated data
        """
        load_dish_cfg_aggregator = LoadDishCfgCommandResultAggregator(
            self, self.logger
        )
        (
            load_dish_cfg_aggregated_result,
            message,
        ) = load_dish_cfg_aggregator.aggregate()
        self.load_dish_cfg_aggregated_result = load_dish_cfg_aggregated_result
        if (
            self.load_dish_cfg_aggregated_result == ResultCode.FAILED
            and self.load_dish_cfg_command_id
        ):
            exception_message = f"Exception occurred on device: {message}"
            self.long_running_result_callback(
                self.load_dish_cfg_command_id,
                ResultCode.FAILED,
                exception_msg=exception_message,
            )

    def reset_load_dish_cfg_data(self) -> None:
        """Reset all data which is set for aggregating LoadDisgCfg command"""
        self.logger.info("Resetting LoadDishCfg aggregated data")
        self.load_dish_cfg_aggregated_result = ""
        self.dev_names_for_load_dish_cfg = []
        self.result_codes_mapping = {}
        self.load_dish_cfg_command_id = None

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

    def is_subarray_in_right_obs_state(
        self, subarray_id: int, desired_obsstate: List, command_name: str
    ) -> bool:
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
        subarray_devices = self.input_parameter.subarray_dev_names
        for device in subarray_devices:
            subarray_device_id = re.findall(r"\d+", device)
            if subarray_id == int(subarray_device_id[0]):
                subarray_obstate = self.get_device(device).obs_state
                if subarray_obstate not in desired_obsstate:
                    raise StateModelError(
                        f"{command_name} command not permitted in observation "
                        + f"state {subarray_obstate}"
                    )
        return True

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

        # check whether subarray is in proper obstate or not.
        self.is_subarray_in_right_obs_state(
            subarray_id_or_message,
            [ObsState.EMPTY, ObsState.IDLE],
            "AssignResources",
        )

        # Execute the command if the input JSON is valid
        self.logger.info("Calling component manager assign_resources method")
        assign_resources_command = AssignResources(
            self,
            adapter_factory=self.adapter_factory,
            skuid=SkuidClient(self.skuid_service),
            logger=self.logger,
        )

        if isinstance(self.input_parameter, InputParameterLow):
            (
                is_valid,
                invalid_json_error_msg,
            ) = assign_resources_command._validate_low_json(
                input_json_or_message, REQUIRED_LOW_ASSIGN_RESOURCE_KEYS
            )
            if not is_valid:
                return assign_resources_command.reject_command(
                    invalid_json_error_msg
                )
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
            args=[json_argument, self.logger],
            task_callback=task_callback,
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

        # check whether subarray is in proper obstate or not.
        self.is_subarray_in_right_obs_state(
            subarray_id_or_message, [ObsState.IDLE], "ReleaseResources"
        )

        release_resources_command = ReleaseResources(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        # Execute the command if the input JSON is valid
        if isinstance(self.input_parameter, InputParameterLow):
            (
                is_valid,
                invalid_json_error_msg,
            ) = release_resources_command._validate_low_json(
                input_json_or_message,
                REQUIRED_LOW_RELEASE_RESOURCE_KEYS,
            )
            if not is_valid:
                return release_resources_command.reject_command(
                    invalid_json_error_msg
                )
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
            args=[json.dumps(input_json_or_message), self.logger],
            task_callback=task_callback,
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
        """blank method for resolving pylint errors"""

    def off(self):
        """blank method for resolving pylint errors"""

    def on(self):
        """blank method for resolving pylint errors"""

    def start_communicating(self):
        """blank method for resolving pylint errors"""

    def stop_communicating(self):
        """blank method for resolving pylint errors"""

    def standby(self):
        """blank method for resolving pylint errors"""

    def _aggregate_health_state(self):
        """
        Aggregates all health states
        and call the relative callback if available
        """

    def _aggregate_telescope_state(self):
        """
        Aggregates telescope state
        """

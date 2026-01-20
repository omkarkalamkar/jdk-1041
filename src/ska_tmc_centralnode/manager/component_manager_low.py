"""
This module is inherited from CNComponentManager.

It is component Manager for Low Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""

import json
import time
from collections import defaultdict
from logging import Logger
from queue import Queue
from typing import Callable, Dict

from ska_control_model import AdminMode
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_telmodel.schema import validate
from ska_tmc_common.enum import LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command_low import (
    AssignResourcesLow,
)
from ska_tmc_centralnode.commands.release_resources_command_low import (
    ReleaseResourcesLow,
)
from ska_tmc_centralnode.manager.aggregate_process import (
    HealthStateAggregationProcessor,
)
from ska_tmc_centralnode.manager.aggregators import (
    TelescopeAvailabilityAggregatorLow,
    TelescopeStateAggregatorLow,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.utils.constants import (
    LOW_ASSIGN_RESOURCES_SCHEMA_VERSION,
    LOW_RELEASE_RESOURCES_SCHEMA_VERSION,
)


class CNComponentManagerLow(CNComponentManager):
    """Component Manager class for low central node"""

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
        _event_manager=True,
        proxy_timeout=500,
        event_subscription_check_period=1,
        liveliness_check_period=1,
        command_timeout=30,
        subarray_trl_prefix: str = "low-tmc/subarray/",
        is_auto_recovery_enabled: bool = True,
        default_array_layout_url: dict | None = None,
        *args,
        **kwargs,
    ):
        """
        Initialise a new ComponentManager instance for low.

        :param op_state_model: the op state model used by this component
            manager
        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        :param _input_parameter : specify input parameter for low.
        :param _liveliness_probe:allows to enable/disable LivelinessProbe usage
        :param _event_manager : allows to enable/disable EventManager usage
        :param max_workers: Optional. Maximum worker threads for
            monitoring purpose.
        :param proxy_timeout: Optional. Time period to wait for
            event and responses.
        :param event_subscription_check_period: (int) Time in seconds for sleep
            intervals in the event subsription thread.
        :param liveliness_check_period: (int) Period for the liveliness probe
            to monitor each device in a loop
        :param timeout : Optional. Time period to wait for
            intialization of adapter.
        """
        super().__init__(
            op_state_model,
            _input_parameter,
            logger,
            _update_device_callback,
            _update_telescope_state_callback,
            _update_telescope_health_state_callback,
            _update_tmc_op_state_callback,
            _update_imaging_callback,
            _telescope_availability_callback,
            array_layout_url_callback,
            default_array_layout_url_callback,
            _component,
            _liveliness_probe,
            _event_manager,
            proxy_timeout,
            command_timeout=command_timeout,
            event_subscription_check_period=event_subscription_check_period,
            liveliness_check_period=liveliness_check_period,
            subarray_trl_prefix=subarray_trl_prefix,
            default_array_layout_url=default_array_layout_url,
            *args,
            **kwargs,
        )
        self.is_auto_recovery_enabled = is_auto_recovery_enabled
        self._telescope_availability_aggregator = None
        self.subarray_availability = {
            subarray: False
            for subarray in self.input_parameter.subarray_dev_names
        }
        self.csp_mln_availability = False
        self.sdp_mln_availability = False
        self.mccs_mln_availability = False
        telescope_availability = self.get_telescope_availability()
        self._assign_resources_schema_version: str = (
            LOW_ASSIGN_RESOURCES_SCHEMA_VERSION
        )
        self._release_resources_schema_version: str = (
            LOW_RELEASE_RESOURCES_SCHEMA_VERSION
        )
        telescope_availability["tmc_subarrays"] = self.subarray_availability
        self.set_telescope_availability(telescope_availability)

        self._telescope_availability_aggregator = (
            TelescopeAvailabilityAggregatorLow(self, self.logger)
        )
        self.event_dict: dict = {}
        self.error_count: int = 0
        self.event_queue.update(
            {
                "longRunningCommandResult": Queue(),
                "isSubsystemAvailable": Queue(),
                "isSubarrayAvailable": Queue(),
                "state": Queue(),
            }
        )

        self.event_processing_methods.update(
            {
                "longRunningCommandResult": (
                    self.update_long_running_command_result
                ),
                "isSubsystemAvailable": self.update_telescope_availability,
                "isSubarrayAvailable": self.update_telescope_availability,
                "state": self.update_device_state,
            }
        )
        self._start_event_processing_threads()
        # start the aggregation process
        self.aggregation_process = HealthStateAggregationProcessor(
            self.event_data_queue,
            self.aggregated_health_state,
            self.aggregate_value_update_event,
            telescope="low",
        )
        self.aggregation_process.start_aggregation_process()
        self.subsystem_assigned_per_subarray: Dict[int, list] = defaultdict(
            list
        )
        self.subsystem_assigned_per_command_id: Dict[int, list] = defaultdict(
            list
        )
        self.pss_beams_assigned_per_subarray: Dict[int, list] = defaultdict(
            list
        )

    @property
    def assign_resources_schema_version(self) -> str:
        """
        Gets the schema version assigned to resources.

        Returns:
            str: The current value of the assign_resources_schema_version.
        """

        return self._assign_resources_schema_version

    @assign_resources_schema_version.setter
    def assign_resources_schema_version(self, value: str) -> None:
        """
        Sets the schema version for assigned resources.

        Args:
            value (str): The new schema version to be set.
        """

        if self._assign_resources_schema_version != value:
            self._assign_resources_schema_version = value

    @property
    def release_resources_schema_version(self) -> str:
        """
        Gets the schema version release the assigned resources.

        Returns:
            str: The current value of the release_resources_schema_version.
        """

        return self._release_resources_schema_version

    @release_resources_schema_version.setter
    def release_resources_schema_version(self, value: str) -> None:
        """
        Sets the schema version for release the assigned resources.

        Args:
            value (str): The new schema version to be set.
        """

        if self._release_resources_schema_version != value:
            self._release_resources_schema_version = value

    def check_if_mccs_mln_is_responsive(self):
        """Checks whether mccs mln is responsive"""
        return self._check_if_device_is_responsive(
            [self.input_parameter.mccs_mln_dev_name]
        )

    def reset_event_count(self, command_id: str):
        """Reset count function to reset sdp and csp events count and
        error dictionary"""
        del self.event_dict[command_id]
        self.error_count = 0
        del self.command_mapping[command_id]
        self.logger.debug(
            "Command mapping dictionary: %s and event dictionary: %s",
            str(self.command_mapping),
            str(self.event_dict),
        )

    def get_unique_ids(self) -> list:
        """Provides unique id for processing long
        running command result events.

        Returns:
            list: Provides list of unique ids under progress
        """
        unique_ids = []
        for data in self.command_mapping.values():
            for uid in data:
                unique_ids.append(uid)
        return unique_ids

    def update_long_running_command_result(self, dev_name: str, value: tuple):
        """Updates the LRCR callback with received event.

        Value contains (unique_id, ResultCode) or (unique_id,exception_msg) or
        (unique_id,TaskStatus)Whenever there is exception occured on any
        device,(unique_id,exception_msg) event is first raised and catched in
        ValueError.The events on longRunningCommandResult from both the
        devices are aggregated and then exception_msg and command_id along
        with the device name is then passed to long_running_result_callback.
        Command_mapping contains {centralnode_command_id:unique_id} , all
        events are verified with respect to this mapping.If there is no
        command_mapping present the event might be of old command.

        :param dev_name: name of the device who's event has been captured
        :type dev_name: str
        :param value: longRunningCommandResult attribute event.
        :type value: tuple
        """
        self.logger.debug(
            "Command mapping dictionary: %s", str(self.command_mapping)
        )
        unique_ids = self.get_unique_ids()
        unique_id, result_code_or_exception_or_task_status = value
        if (
            not unique_id.endswith(self.supported_commands)
            or (not result_code_or_exception_or_task_status)
            or (unique_id not in unique_ids)
        ):  # ignoring other command events
            return

        command_id = self.get_command_id(unique_id)
        self.logger.debug(
            "Command ID: %s | Received longRunningCommandResult event "
            + "for device: %s, with value: %s",
            command_id,
            dev_name,
            str(value),
        )

        try:
            result_code, message = json.loads(
                result_code_or_exception_or_task_status
            )
            if not self.event_dict.get(command_id):
                self.event_dict[command_id] = {}
            match int(result_code):
                case ResultCode.OK:
                    self.event_dict[command_id].update(
                        {dev_name: ResultCode.OK}
                    )
                    self.command_mapping[command_id].remove(unique_id)
                    self.logger.debug(
                        "Updated command mapping dictionary is: %s",
                        str(self.command_mapping),
                    )

                case (
                    ResultCode.REJECTED
                    | ResultCode.FAILED
                    | ResultCode.NOT_ALLOWED
                    | ResultCode.ABORTED
                ):
                    self.event_dict[command_id].update(
                        {dev_name: {"error": message}}
                    )
                    self.error_count += 1
                    self.command_mapping[command_id].remove(unique_id)
                    self.logger.debug(
                        "Updated command mapping dictionary is: %s",
                        str(self.command_mapping),
                    )
                    self.logger.exception(
                        "Command ID: %s | Exception occurred with value: %s "
                        + "for %s command_id for device: %s",
                        command_id,
                        str(value),
                        command_id,
                        dev_name,
                    )
            # If mccs is present in subsystems_to_config list, two LRCR events
            # need to be considered as the command gets invoked on both
            # SubarrayNode and MCCS subsystem.
            if (
                "mccs" in self.subsystem_assigned_per_command_id[command_id]
                and not self.is_auto_recovery_enabled
            ):
                expected_event_dict_len = 2
            else:
                expected_event_dict_len = 1

            if len(self.event_dict[command_id]) == expected_event_dict_len:
                self.logger.info(
                    "Triggering update of long running command result callback"
                )
                self.update_long_running_command_result_callback(command_id)
        except Exception as exception:
            self.logger.exception(
                "Command ID: %s | "
                + "Exception occurred while processing"
                + "long running command result"
                + "attribute event: %s",
                command_id,
                exception,
            )

    def update_long_running_command_result_callback(self, command_id) -> None:
        """
        Checks for errors after receiving events from all the desired devices.
        If there are errors, aggregates them and updates the long running
        command result (LRCR) callback. If there are no errors,
        resets the event dictionary.

        Args:
            command_id (str): The command ID for which to update the LRCR
                callback.
        """
        if self.error_count:
            # Aggregate error messages from event_dict
            exception_message = "Exception occurred on the following devices: "
            for devname, data in self.event_dict[command_id].items():
                if isinstance(data, dict):
                    error_message = data["error"]
                    exception_message += (
                        f"{command_id}: {devname}: {error_message}"
                    )
            self.logger.debug(
                "Command ID: %s | Updating LRCRCallback with following"
                + " values: ResultCode: %s, Message: %s",
                command_id,
                str(ResultCode.FAILED),
                exception_message,
            )
            self.long_running_result_callback(
                command_id,
                ResultCode.FAILED,
                exception_msg=exception_message,
            )
            self.observable.notify_observers(command_exception=True)
        self.reset_event_count(command_id)

    def update_device_state(self, device_name, state):
        """
        Update a monitored device state,
        aggregate the states available
        and call the relative callbacks if available

        :param device_name: name of the device
        :type device_name: str
        :param state: state of the device
        :type state: DevState
        """
        with self.rlock:
            self.logger.debug("State event for %s: %s", device_name, state)
            if "sdp" in device_name:
                # Update SDP Master device name with full FQDN in case of
                # real SDP
                sdp_master_dev_name = self.get_sdp_master_dev_name()
                if device_name in sdp_master_dev_name:
                    device_name = sdp_master_dev_name
            if "csp" in device_name:
                # Update CSP Master device name with full FQDN in case of
                # real CSP
                csp_master_dev_name = self.get_csp_master_dev_name()
                if device_name in csp_master_dev_name:
                    device_name = csp_master_dev_name

            devInfo = self.component.get_device(device_name)
            if devInfo is not None:
                devInfo.state = state
                self.logger.debug(
                    "Updated State of %s: %s ", devInfo.dev_name, devInfo.state
                )
                devInfo.last_event_arrived = time.time()
                self.component._invoke_device_callback(devInfo)

        self._aggregate_state()

    def _aggregate_telescope_state(self):
        """
        Aggregates telescope state
        """
        if self._telescope_state_aggregator is None:
            self._telescope_state_aggregator = TelescopeStateAggregatorLow(
                self, self.logger
            )

        with self.rlock:
            new_state = self._telescope_state_aggregator.aggregate()
            self.component.telescope_state = new_state

    def stop_aggregation_process(self):
        """Stop aggregation process"""
        self.aggregation_process.stop_aggregation_process()

    def check_if_mccs_mln_is_available(self) -> bool:
        """
        Returns boolean value based on availability of MccsMasterLeafNode,
        which indicated availability of Mccs Master.

        Returns:
            bool: boolean value based on availability of
            MccsMasterLeafNode

        """
        telescope_availability = self.get_telescope_availability()
        if not telescope_availability["mccs_master_leaf_node"] is True:
            self.logger.info(
                "MccsMasterLeafNode is not available to receive command"
            )
            return False
        return True

    def is_command_allowed(self, command_name=None) -> bool:
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
        if not self.is_valid_admin_mode():
            raise CommandNotAllowed(
                "One or more controller devices are in "
                "adminMode OFFLINE or NOT-FITTED"
            )
        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                "Command is not allowed in current state :",
                f"{str(self.op_state_model.op_state)}",
            )
        return True

    def check_device_responsiveness_command(
        self, command_name: str, subarray_id: int
    ) -> None:
        """
        This method overrides the method from super class
        to add responsive checks for the devices

        Args:
            command_name (str): Command name for the check
            subarray_id (int): Subarray id

        """
        super().check_device_responsiveness_command(command_name, subarray_id)
        if command_name in self.supported_commands_for_responsive_check:
            self.check_if_mccs_mln_is_responsive()

    def update_telescope_availability(self, device_name, event_value):
        """Updates telescope availability"""
        with self.rlock:
            self.logger.debug("Device name is: %s", device_name)
            self.logger.debug("Event value is: %s", event_value)

            if device_name in self.input_parameter.subarray_dev_names:
                self.subarray_availability[device_name] = event_value
            elif self.input_parameter.csp_mln_dev_name == device_name:
                self.csp_mln_availability = event_value
            elif self.input_parameter.sdp_mln_dev_name == device_name:
                self.sdp_mln_availability = event_value
            elif self.input_parameter.mccs_mln_dev_name == device_name:
                self.mccs_mln_availability = event_value
            self._telescope_availability_aggregator.aggregate()

    def is_valid_admin_mode(self) -> bool:
        """
        Extends the base admin mode validation with MCCS
        check for LOW telescope.

        Returns:
            bool: True if all controllers including MCCS
            are in valid admin mode.
        """
        sdp_admin_mode = self.get_sdp_controller_admin_mode()
        csp_admin_mode = self.get_csp_controller_admin_mode()
        mccs_admin_mode = self.get_mccs_controller_admin_mode()
        admin_modes = [sdp_admin_mode, csp_admin_mode, mccs_admin_mode]

        if any(
            mode in [AdminMode.OFFLINE, AdminMode.NOT_FITTED]
            for mode in admin_modes
        ):
            self.logger.debug(
                "AdminMode check failed: SDP=%s, CSP=%s, MCCS=%s",
                sdp_admin_mode,
                csp_admin_mode,
                mccs_admin_mode,
            )
            return False

        return True

    def validate_assign_json(self, argin: str):
        """Validates the assign resources json.

        :param argin: Assign resources json string.
        :type argin: str
        """
        json_argument = json.loads(argin)
        self.validate_subarray_id(json_argument)

        interface = (
            json_argument.get("interface", None)
            or self._assign_resources_schema_version
        )
        validate(
            version=interface,
            config=json_argument,
            strictness=2,
        )

    def assign_resources(self, argin: str, task_callback: TaskCallbackType):
        """
        Submits the AssignResources command in queue.

        :param argin: input json string for assign resource command
        :type argin: str
        :param task_callback: Updates task status
        :type task_callback: TaskCallbackType
        :return: task_status
        :rtype: tuple
        """
        try:
            assign_resources_command = AssignResourcesLow(
                self,
                adapter_factory=self.adapter_factory,
                logger=self.logger,
                is_auto_recovery_enabled=self.is_auto_recovery_enabled,
            )
            self.validate_assign_json(argin)
            assign_resources_command.subarray_id = self.get_subarray_id(argin)
            task_status, response = self.submit_task(
                assign_resources_command.assign_resources,
                kwargs={"argin": argin},
                task_callback=task_callback,
                is_cmd_allowed=self.command_not_allowed_callable(
                    self.get_subarray_id(argin),
                    [ObsState.EMPTY, ObsState.IDLE],
                    "AssignResources",
                ),
            )
            self.logger.info(
                "AssignResources command's status: "
                + f"{task_status.name}, and response: {response}"
            )

            return task_status, response
        except Exception as exception:
            self.logger.exception(
                "Exception occurred while processing " + "assignresource: %s ",
                exception,
            )
            return assign_resources_command.reject_command(str(exception))

    def validate_release_json(self, argin: str):
        """Validates the release resource json.

        :param argin: release resource json string.
        :type argin: str
        """
        json_argument = json.loads(argin)
        self.validate_subarray_id(json_argument)
        interface = (
            json_argument.get("interface", None)
            or self._release_resources_schema_version
        )
        validate(
            version=interface,
            config=json_argument,
            strictness=2,
        )

    def release_resources(self, argin: str, task_callback: TaskCallbackType):
        """
        Submit the ReleaseResource command in queue.

        :param argin: input json string for release resource command
        :type argin: str
        :param task_callback: Updates task status
        :type task_callback: TaskCallbackType
        :return: task_status
        :rtype: tuple
        """
        try:
            release_resources_command = ReleaseResourcesLow(
                self,
                adapter_factory=self.adapter_factory,
                logger=self.logger,
                is_auto_recovery_enabled=self.is_auto_recovery_enabled,
            )
            self.validate_release_json(argin)

            self.check_availability_for_release(argin)
            release_resources_command.subarray_id = self.get_subarray_id(argin)
            task_status, response = self.submit_task(
                release_resources_command.release_resources,
                kwargs={"argin": argin},
                task_callback=task_callback,
                is_cmd_allowed=self.command_not_allowed_callable(
                    self.get_subarray_id(argin),
                    [ObsState.IDLE],
                    "ReleaseResources",
                ),
            )
            self.logger.info(
                "ReleaseResources command's status: "
                + f"{task_status.name}, and response: {response}"
            )

            return task_status, response
        except Exception as exception:
            return release_resources_command.reject_command(str(exception))

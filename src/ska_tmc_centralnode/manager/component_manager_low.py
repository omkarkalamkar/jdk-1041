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
from typing import Callable, Dict, Tuple

from ska_control_model import AdminMode, ResultCode, TaskStatus
from ska_schemas.schema import validate
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.faults import StateModelError
from ska_tmc_common.enum import LivelinessProbeType
from ska_tmc_common.exceptions import (
    CommandNotAllowed,
    SubarrayNotPresentError,
)
from tango import DevState

from ska_tmc_centralnode.manager.aggregate_process import (
    HealthStateAggregationProcessor,
)
from ska_tmc_centralnode.manager.aggregators import (
    TelescopeAvailabilityAggregatorLow,
    TelescopeStateAggregatorLow,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.refactored_commands.assignresources import (
    ArrayLayoutContext,
    CommandInProgressContext,
    LowAssignResourcesContext,
    ObsStateContext,
)
from ska_tmc_centralnode.refactored_commands.releaseresources import (
    LowReleaseResourcesContext,
    ReleaseResourcesLow,
)
from ska_tmc_centralnode.utils.constants import (
    LOW_ASSIGN_RESOURCES_SCHEMA_VERSION,
    LOW_RELEASE_RESOURCES_SCHEMA_VERSION,
)

from ..refactored_commands.assignresources import assign_resources_command_low

AssignResourcesLow = assign_resources_command_low.AssignResourcesLow


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
            self.logger.debug(
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

    def validate_assign_json(self, argin: str) -> Tuple[str, str]:
        """Validates the assign resources json.

        :param argin: Assign resources json string.
        :type argin: str

        :return: Returns the original argument and exception message.
        :rtype: tuple[str, str]
        """
        exception_msg: str = ""
        try:
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
            self.update_subarray_pss_beams_mapping(json_argument)
        except Exception as exception:
            exception_msg = str(exception)
            self.logger.exception(
                "Exception occurred while processing assignresource: %s ",
                exception_msg,
            )
        return argin, exception_msg

    def set_subsystem_assigned_per_subarray(
        self, subarray_id: int, subsystems: list
    ) -> None:
        """Sets the assigned subsystems for a given subarray.

        :param subarray_id: The ID of the subarray.
        :type subarray_id: int
        :param subsystems: List of subsystems assigned to the subarray.
        :type subsystems: list
        """
        self.subsystem_assigned_per_subarray[subarray_id] = subsystems

    def set_pss_beams_assigned_per_subarray(
        self, subarray_id: int, pss_beams: list
    ) -> None:
        """Sets the assigned PSS beams for a given subarray.

        :param subarray_id: The ID of the subarray.
        :type subarray_id: int
        :param pss_beams: List of PSS beams assigned to the subarray.
        :type pss_beams: list
        """
        self.pss_beams_assigned_per_subarray[subarray_id] = pss_beams

    def pop_subsystem_assigned_per_subarray_id(self, subarray_id: int) -> None:
        """Pops the assigned subsystems for a given subarray ID.

        :param subarray_id: The ID of the subarray.
        :type subarray_id: int
        :return: List of subsystems assigned to the subarray.
        :rtype: list
        """
        self.subsystem_assigned_per_subarray.pop(subarray_id, None)
        self.pss_beams_assigned_per_subarray.pop(subarray_id, None)

    def _get_assign_context(self) -> LowAssignResourcesContext:
        """Build LowAssignResourcesContext bound to this component manager.

        :return: Runtime context for AssignResources command execution.
        :rtype: LowAssignResourcesContext
        """
        return LowAssignResourcesContext(
            command_completion_condition=self.command_completion_cond,
            command_timeout=self.command_timeout,
            cmd_inprogress_ctx=CommandInProgressContext(
                update_name=lambda name: setattr(
                    self, "command_in_progress", name
                ),
                clear=lambda _: setattr(self, "command_in_progress", ""),
                get_name=lambda: self.command_in_progress,
            ),
            array_layout_ctx=ArrayLayoutContext(
                update_url=lambda url: setattr(self, "array_layout_url", url),
                get_default_url=lambda: self.default_array_layout_url,
            ),
            obs_state_ctx=ObsStateContext(
                get=self.get_subarray_obsstate,
            ),
            input_parameter=self.input_parameter,
            update_abort_evt=lambda evt: setattr(self, "abort_event", evt),
            is_auto_recovery_enabled=self.is_auto_recovery_enabled,
            get_assigned_subsystems=self.subsystem_assigned_per_subarray,
            set_assigned_subsystems=self.set_subsystem_assigned_per_subarray,
            log_state=self.log_state,
            subarray_trl_prefix=self.subarray_trl_prefix,
        )

    def _get_release_context(self) -> LowReleaseResourcesContext:
        """Build LowReleaseResourcesContext bound to this component manager."""
        return LowReleaseResourcesContext(
            command_completion_condition=self.command_completion_cond,
            cmd_inprogress_ctx=CommandInProgressContext(
                update_name=lambda name: setattr(
                    self, "command_in_progress", name
                ),
                clear=lambda _: setattr(self, "command_in_progress", ""),
                get_name=lambda: self.command_in_progress,
            ),
            command_timeout=self.command_timeout,
            input_parameter=self.input_parameter,
            obs_state_ctx=ObsStateContext(
                get=self.get_subarray_obsstate,
            ),
            is_auto_recovery_enabled=self.is_auto_recovery_enabled,
            update_abort_evt=lambda evt: setattr(self, "abort_event", evt),
            subarray_trl_prefix=self.subarray_trl_prefix,
            pop_subsystem_assigned_per_subarray_id=(
                self.pop_subsystem_assigned_per_subarray_id
            ),
            get_assigned_subsystems=(
                lambda: self.subsystem_assigned_per_subarray
            ),
            set_assigned_subsystems=self.set_subsystem_assigned_per_subarray,
        )

    # pylint: disable=unexpected-keyword-arg
    def assign_resources(
        self, argin: str, task_callback: TaskCallbackType, task_abort_event
    ) -> Tuple[TaskStatus, str]:
        """
        Submits the AssignResources command in queue.

        :param argin: input json string for assign resource command
        :type argin: str
        :param task_callback: Updates task status
        :type task_callback: TaskCallbackType
        :param task_abort_event: Event to abort the task
        :type task_abort_event: Event
        :return: task_status
        :rtype: tuple
        """
        try:
            assign_resources_command_object = AssignResourcesLow(
                adapter_provider=self.adapter_factory,
                logger=self.logger,
                command_runtime_context=self._get_assign_context(),
                is_auto_recovery_enabled=self.is_auto_recovery_enabled,
            )
            assign_resources_command_object.subarray_id = self.get_subarray_id(
                argin
            )
            # Validate command is allowed
            self.is_command_allowed_before_lrc_start(
                subarray_id=assign_resources_command_object.subarray_id,
                command_name="AssignResources",
            )
            return assign_resources_command_object.execute(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        except (StateModelError, CommandNotAllowed) as exception:
            self.logger.exception(
                "Exception occurred while processing " + "assignresource: %s ",
                exception,
            )
            return task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )
        except Exception as exception:
            self.logger.exception(
                "Exception occurred while processing " + "assignresource: %s ",
                exception,
            )
            return task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, str(exception)),
            )

    # pylint: enable=unexpected-keyword-arg

    def validate_release_json(self, argin: str) -> Tuple[str, str]:
        """Validates the release resource json.

        :param argin: release resource json string.
        :type argin: str

        :return: Returns the original argument and exception message.
        :rtype: tuple[str, str]
        """
        exception_msg: str = ""
        try:
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
        except Exception as exception:
            exception_msg = str(exception)
            self.logger.exception(
                "Exception occurred while processing releaseresource: %s ",
                exception_msg,
            )
        return argin, exception_msg

    # pylint: disable=unexpected-keyword-arg
    def release_resources(
        self, argin: str, task_callback: TaskCallbackType, task_abort_event
    ) -> Tuple[TaskStatus, str]:
        """
        Submit the ReleaseResource command in queue.

        :param argin: input json string for release resource command
        :type argin: str
        :param task_callback: Updates task status
        :type task_callback: TaskCallbackType
        :param task_abort_event: Event to abort the task
        :type task_abort_event: Event
        :return: task_status
        :rtype: tuple
        """
        try:
            release_resources_command_object = ReleaseResourcesLow(
                adapter_provider=self.adapter_factory,
                logger=self.logger,
                command_runtime_context=self._get_release_context(),
                is_auto_recovery_enabled=self.is_auto_recovery_enabled,
            )

            self.check_availability_for_release(argin)
            release_resources_command_object.subarray_id = (
                self.get_subarray_id(argin)
            )
            # Validate command is allowed
            self.is_command_allowed_before_lrc_start(
                subarray_id=release_resources_command_object.subarray_id,
                command_name="ReleaseResources",
            )
            return release_resources_command_object.execute(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        except (
            StateModelError,
            CommandNotAllowed,
            SubarrayNotPresentError,
        ) as exception:
            self.logger.exception(
                "Exception occurred while processing "
                + "releaseresource: %s ",
                exception,
            )
            return task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )

        except Exception as exception:
            self.logger.exception(
                "Exception occurred while processing "
                + "releaseresource: %s ",
                exception,
            )
            return task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, str(exception)),
            )

    # pylint: enable=unexpected-keyword-arg

    def update_subarray_pss_beams_mapping(self, json_argument: dict) -> dict:
        """
        Method to update the mapping of subarray_id to the assigned pss beams

        Args:
            json_argument (dict): The string in JSON format.

        Returns:
            dict: The string in JSON format.

        """
        try:
            subarray_id = json_argument["subarray_id"]
            csp_input = json_argument.get("csp", None)
            if csp_input is None:
                self.logger.debug("csp key missing")
                return
            pss_key = csp_input.get("pss", None)
            if pss_key is None:
                return
            pss_beam_ids = pss_key["pss_beam_ids"]
            assigned_pss_beams = set()
            for (
                assigned_subarray_id,
                beams,
            ) in self.pss_beams_assigned_per_subarray.items():
                if assigned_subarray_id != subarray_id:
                    assigned_pss_beams.update(beams)

            # Check if pss_beam_id is already assigned to another subarray
            conflicting_beams = [
                beam for beam in pss_beam_ids if beam in assigned_pss_beams
            ]
            if conflicting_beams:
                self.logger.error(
                    "PSS beams: %s already assigned to another subarray",
                    conflicting_beams,
                )
                raise Exception(
                    f"PSS beams: {conflicting_beams} already assigned"
                    f" to another subarray"
                )
            self.logger.debug(
                "PSS beams assigned for subarray %s: %s",
                subarray_id,
                pss_beam_ids,
            )
            self.pss_beams_assigned_per_subarray[subarray_id] = pss_beam_ids

        except Exception as exception:
            raise exception

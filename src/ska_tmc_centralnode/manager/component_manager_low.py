"""
This module is inherited from CNComponentManager.

It is component Manager for Low Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""

import json
from collections import defaultdict
from typing import Callable, Dict, Tuple

from ska_schemas.schema import validate
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.software_bus import Signal
from ska_tmc_common import DeviceInfo, SubArrayDeviceInfo

from ska_tmc_centralnode.manager.aggregate_process import (
    HealthStateAggregationProcessor,
)
from ska_tmc_centralnode.manager.aggregators import (
    TelescopeAvailabilityAggregatorLow,
    TelescopeStateAggregatorLow,
)
from ska_tmc_centralnode.manager.command_allowance_validator import (
    LowCommandAllowanceValidator,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.manager.component_manager_config import (
    LowCentralNodeComponentManagerConfig,
)
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

from ..model.component import MCCSDeviceInfo
from ..model.input import InputParameterLow
from ..refactored_commands.assignresources import assign_resources_command_low
from ..utils.exception_decorator import exception_handler
from .event_callback_manager.low_event_callback_manager import (
    LowEventCallbackContext,
    LowEventCallbackManager,
)

AssignResourcesLow = assign_resources_command_low.AssignResourcesLow


class SubarrayPSSMappingError(Exception):
    """Raised whenever there is an issue with PSS and subarray mapping"""


class CNComponentManagerLow(CNComponentManager[InputParameterLow]):
    """Component Manager class for low central node"""

    _assign_resources_schema_version: Signal = Signal[str](
        stored=True, initial_value=LOW_ASSIGN_RESOURCES_SCHEMA_VERSION
    )
    _release_resources_schema_version: Signal = Signal[str](
        stored=True, initial_value=LOW_RELEASE_RESOURCES_SCHEMA_VERSION
    )

    # pylint:disable=keyword-arg-before-vararg
    def __init__(self, config: LowCentralNodeComponentManagerConfig):
        """
        Initialise a new ComponentManager instance for low.

        Args:
            config:
        """

        super().__init__(config=config)
        self.config = config
        self._telescope_availability_aggregator = None
        self.csp_mln_availability = False
        self.sdp_mln_availability = False
        self.mccs_mln_availability = False

        self._telescope_availability_aggregator = (
            TelescopeAvailabilityAggregatorLow(self, self.logger)
        )
        self.cmd_allowed_validator = LowCommandAllowanceValidator(
            self.logger,
            self.get_device,
            self.input_parameter,
            self.config.subarray_trl_prefix,
            self.config.retry_attempts,
            self.config.retry_delay,
            adapter_factory=self.adapter_factory,
            get_op_state_model=lambda: self.config.op_state_model,
        )
        self._event_cb_manager: LowEventCallbackManager = (
            self._get_event_cb_manager()
        )
        self._register_event_handlers(self._get_event_handlers())
        self.event_processor.start()
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

    def _get_event_cb_manager(self) -> LowEventCallbackManager:
        """Provides Instance Event Callaback Manager"""
        return LowEventCallbackManager(
            context=LowEventCallbackContext(
                **self.get_event_cb_manager_context(),
                _telescope_availability_aggregator=(
                    self._telescope_availability_aggregator
                ),
                update_subarray_availability=self.update_subarray_availability,
                set_csp_mln_availability=lambda availability: setattr(
                    self, "csp_mln_availability", availability
                ),
                set_sdp_mln_availability=lambda availability: setattr(
                    self, "sdp_mln_availability", availability
                ),
                set_mccs_mln_availability=lambda availability: setattr(
                    self, "mccs_mln_availability", availability
                ),
            )
        )

    def _get_event_handlers(self) -> Dict[str, Callable]:
        """Returns event handlers with addition of low specific.

        :return: Dictionary with attribute name and its event handler.
        :rtype: dict
        """
        event_handlers: dict = super()._get_event_handlers()
        event_handlers.update(
            {
                "isSubsystemAvailable": (
                    self._event_cb_manager.update_telescope_availability
                ),
                "isSubarrayAvailable": (
                    self._event_cb_manager.update_telescope_availability
                ),
                "state": self._event_cb_manager.update_device_state,
            }
        )
        return event_handlers

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

    def create_device_info(
        self, device_name: str
    ) -> SubArrayDeviceInfo | MCCSDeviceInfo | DeviceInfo:
        """Creates the device information for device.

        :param device_name: Name of device.
        :type device_name: str
        :return: DeviceInfo Instance
        :rtype: SubArrayDeviceInfo or DeviceInfo or MCCSDeviceInfo
        """
        dev_info: SubArrayDeviceInfo = super().create_device_info(device_name)
        if (
            not dev_info
            and device_name.lower()
            in self.get_mccs_master_leaf_node_dev_name()
        ):
            dev_info = MCCSDeviceInfo(device_name, False)
        elif not dev_info:
            dev_info = DeviceInfo(device_name, False)

        return dev_info

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
        if not telescope_availability.get("mccs_master_leaf_node", False):
            self.logger.debug(
                "MccsMasterLeafNode is not available to receive command"
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
            json_argument["interface"] = interface
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
            command_timeout=self.config.timeout_config.command_timeout,
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
            is_auto_recovery_enabled=self.config.is_auto_recovery_enabled,
            get_assigned_subsystems=(
                lambda: self.subsystem_assigned_per_subarray
            ),
            set_assigned_subsystems=self.set_subsystem_assigned_per_subarray,
            log_state=self.log_state,
            subarray_trl_prefix=self.config.subarray_trl_prefix,
            mccs_mln_dev_name=self.input_parameter.mccs_mln_dev_name,
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
            command_timeout=self.config.timeout_config.command_timeout,
            input_parameter=self.input_parameter,
            obs_state_ctx=ObsStateContext(
                get=self.get_subarray_obsstate,
            ),
            is_auto_recovery_enabled=self.config.is_auto_recovery_enabled,
            update_abort_evt=lambda evt: setattr(self, "abort_event", evt),
            subarray_trl_prefix=self.config.subarray_trl_prefix,
            pop_subsystem_assigned_per_subarray_id=(
                self.pop_subsystem_assigned_per_subarray_id
            ),
            get_assigned_subsystems=(
                lambda: self.subsystem_assigned_per_subarray
            ),
            set_assigned_subsystems=self.set_subsystem_assigned_per_subarray,
            mccs_mln_dev_name=self.input_parameter.mccs_mln_dev_name,
        )

    @exception_handler("AssignResources")
    def assign_resources(
        self, argin: str, task_callback: TaskCallbackType, task_abort_event
    ) -> None:
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
        assign_resources_command_object = AssignResourcesLow(
            adapter_provider=self.adapter_factory,
            logger=self.logger,
            command_runtime_context=self._get_assign_context(),
            is_auto_recovery_enabled=self.config.is_auto_recovery_enabled,
        )
        assign_resources_command_object.subarray_id = self.get_subarray_id(
            argin
        )
        # Validate command is allowed
        self.cmd_allowed_validator.is_command_allowed_before_lrc_start(
            subarray_id=assign_resources_command_object.subarray_id,
            command_name="AssignResources",
        )
        assign_resources_command_object.execute(
            argin=argin,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

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
                json_argument.get("interface")
                or self.release_resources_schema_version
            )
            json_argument["interface"] = interface
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

    @exception_handler("ReleaseResources")
    def release_resources(
        self, argin: str, task_callback: TaskCallbackType, task_abort_event
    ) -> None:
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
        release_resources_command_object = ReleaseResourcesLow(
            adapter_provider=self.adapter_factory,
            logger=self.logger,
            command_runtime_context=self._get_release_context(),
            is_auto_recovery_enabled=self.config.is_auto_recovery_enabled,
        )

        self.check_availability_for_release(argin)
        release_resources_command_object.subarray_id = self.get_subarray_id(
            argin
        )
        # Validate command is allowed
        self.cmd_allowed_validator.is_command_allowed_before_lrc_start(
            subarray_id=release_resources_command_object.subarray_id,
            command_name="ReleaseResources",
        )
        release_resources_command_object.execute(
            argin=argin,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def update_subarray_pss_beams_mapping(self, json_argument: dict) -> None:
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
                raise SubarrayPSSMappingError(
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
            error_msg = (
                "Exception occurred while updating subarray"
                f" and pss beams mapping: {exception}"
            )
            self.logger.error(error_msg)
            raise SubarrayPSSMappingError(error_msg) from exception

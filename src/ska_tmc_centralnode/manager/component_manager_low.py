"""
This module is inherited from CNComponentManager.

It is component Manager for Low Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""

import json
from collections import defaultdict
from typing import Callable, Dict, Tuple

from ska_control_model import ResultCode, TaskStatus
from ska_schemas.schema import validate
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.faults import StateModelError
from ska_tango_base.software_bus import Signal
from ska_tmc_common.exceptions import CommandNotAllowed

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
from ska_tmc_centralnode.manager.command_allowance_validator import (
    LowCommandAllowanceValidator,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.manager.component_manager_config import (
    LowCentralNodeComponentManagerConfig,
)
from ska_tmc_centralnode.utils.constants import (
    LOW_ASSIGN_RESOURCES_SCHEMA_VERSION,
    LOW_RELEASE_RESOURCES_SCHEMA_VERSION,
)

from .event_callback_manager.low_event_callback_manager import (
    LowEventCallbackManager,
)


class CNComponentManagerLow(CNComponentManager):
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
        self.subarray_availability = {
            subarray: False
            for subarray in self.input_parameter.subarray_dev_names
        }
        telescope_availability = self.get_telescope_availability()
        telescope_availability["tmc_subarrays"] = self.subarray_availability
        self.set_telescope_availability(telescope_availability)
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
        self.subsystem_assigned_per_command_id: Dict[int, list] = defaultdict(
            list
        )
        self.pss_beams_assigned_per_subarray: Dict[int, list] = defaultdict(
            list
        )

    def on_new_shared_bus(self) -> None:
        super().on_new_shared_bus()
        self._assign_resources_schema_version = (
            LOW_ASSIGN_RESOURCES_SCHEMA_VERSION
        )
        self._release_resources_schema_version = (
            LOW_RELEASE_RESOURCES_SCHEMA_VERSION
        )

    def _get_event_cb_manager(self) -> LowEventCallbackManager:
        """Provides Instance Event Callaback Manager"""
        return LowEventCallbackManager(
            logger=self.logger,
            component=self.component,
            command_completion_cond=self.command_completion_cond,
            input_parameter=self.input_parameter,
            event_data_manager=self.event_data_manager,
            _aggregate_state=self._aggregate_state,
            _telescope_availability_aggregator=(
                self._telescope_availability_aggregator
            ),
            subarray_availability=self.subarray_availability,
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
        if (
            not telescope_availability.get("mccs_master_leaf_node", False)
            is True
        ):
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

    # pylint: disable=unexpected-keyword-arg
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
        try:
            assign_resources_command_object = AssignResourcesLow(
                self,
                adapter_factory=self.adapter_factory,
                logger=self.logger,
                is_auto_recovery_enabled=self.config.is_auto_recovery_enabled,
            )
            subarray_id = self.get_subarray_id(argin)
            assign_resources_command_object.subarray_id = str(subarray_id)
            # Validate command is allowed
            self.cmd_allowed_validator.is_command_allowed_before_lrc_start(
                subarray_id=subarray_id,
                command_name="AssignResources",
            )
            assign_resources_command_object.assign_resources(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        except (StateModelError, CommandNotAllowed) as exception:
            self.logger.exception(
                "Exception occurred while processing  assignresource: %s ",
                exception,
            )
            task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )
        except Exception as exception:
            self.logger.exception(
                "Exception occurred while processing assignresource: %s ",
                exception,
            )
            task_callback(
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
        try:
            release_resources_command_object = ReleaseResourcesLow(
                self,
                adapter_factory=self.adapter_factory,
                logger=self.logger,
                is_auto_recovery_enabled=self.config.is_auto_recovery_enabled,
            )

            self.check_availability_for_release(argin)
            subarray_id = self.get_subarray_id(argin)
            release_resources_command_object.subarray_id = str(subarray_id)
            # Validate command is allowed
            self.cmd_allowed_validator.is_command_allowed_before_lrc_start(
                subarray_id=subarray_id,
                command_name="ReleaseResources",
            )
            release_resources_command_object.release_resources(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        except (StateModelError, CommandNotAllowed) as exception:
            self.logger.exception(
                "Exception occurred while processing "
                + "releaseresource: %s ",
                exception,
            )
            task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )

        except Exception as exception:
            self.logger.exception(
                "Exception occurred while processing "
                + "releaseresource: %s ",
                exception,
            )
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, str(exception)),
            )

    # pylint: enable=unexpected-keyword-arg

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

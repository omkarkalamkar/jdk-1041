"""
This module is inherited from CNComponentManager.

It is component Manager for Low Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import json
import time

from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from ska_tmc_centralnode.manager.aggregators import (
    HealthStateAggregatorLow,
    TelescopeAvailabilityAggregatorLow,
    TelescopeStateAggregatorLow,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.utils.constants import MCCS_MLN_SUFIX


class CNComponentManagerLow(CNComponentManager):
    """Component Manager class for low central node"""

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
        _telescope_availability_callback=None,
        communication_state_callback=None,
        component_state_callback=None,
        proxy_timeout=500,
        sleep_time=1,
        skuid_service="",
        command_timeout=30,
        assignresources_interface: str = (
            "https://schema.skao.int/ska-low-tmc-assignresources/4.0"
        ),
        releaseresources_interface: str = (
            "https://schema.skao.int/ska-low-tmc-releaseresources/3.0"
        ),
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
        :param _event_receiver : allows to enable/disable EventReceiver usage
        :param max_workers: Optional. Maximum worker threads for
            monitoring purpose.
        :param proxy_timeout: Optional. Time period to wait for
            event and responses.
        :param sleep_time: Optional. Sleep time between reties.
        :param timeout : Optional. Time period to wait for
            intialization of adapter.
        """
        super().__init__(
            op_state_model,
            _input_parameter,
            logger,
            _component,
            _liveliness_probe,
            _event_receiver,
            _update_device_callback,
            _update_telescope_state_callback,
            _update_telescope_health_state_callback,
            _update_tmc_op_state_callback,
            _update_imaging_callback,
            communication_state_callback,
            _telescope_availability_callback,
            component_state_callback,
            proxy_timeout,
            sleep_time,
            skuid_service=skuid_service,
            command_timeout=command_timeout,
            assignresources_interface=assignresources_interface,
            releaseresources_interface=releaseresources_interface,
            *args,
            **kwargs,
        )
        self._telescope_availability_aggregator = None
        self.subarray_availability = {
            subarray: False
            for subarray in self.input_parameter.subarray_dev_names
        }
        self.csp_mln_availability = False
        self.sdp_mln_availability = False
        self.mccs_mln_availability = False

        telescope_availability = self.get_telescope_availability()
        telescope_availability["tmc_subarrays"] = self.subarray_availability
        self.set_telescope_availability = telescope_availability

        self._telescope_availability_aggregator = (
            TelescopeAvailabilityAggregatorLow(self, self.logger)
        )
        self.event_dict: dict = {}
        self.error_count: int = 0

    def check_if_mccs_mln_is_responsive(self):
        """Checks whether mccs mln is responsive"""
        return self._check_if_device_is_responsive(
            [self.input_parameter.mccs_mln_dev_name]
        )

    def reset_event_count(self, command_id: str):
        """Reset count function to reset sdp and csp events count and
        error dictionary"""
        self.event_dict.clear()
        self.error_count = 0
        del self.command_mapping[command_id]
        self.logger.info(
            "Updated command mapping dictionary is: %s", self.command_mapping
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
        self.logger.info(
            "Received longRunningCommandResult event for device: \
                %s, with value: %s",
            dev_name,
            value,
        )
        unique_ids = self.get_unique_ids()

        unique_id, result_code_or_exception_or_task_status = value
        if (
            not unique_id.endswith(self.supported_commands)
            or (not result_code_or_exception_or_task_status)
            or (unique_id not in unique_ids)
        ):  # ignoring other command events
            return
        try:
            result_code, message = json.loads(
                result_code_or_exception_or_task_status
            )
            if not self.event_dict.get(self.command_id):
                self.event_dict[self.command_id] = {}
            match int(result_code):
                case ResultCode.OK:
                    self.event_dict[self.command_id].update(
                        {dev_name: ResultCode.OK}
                    )
                    self.command_mapping[self.command_id].remove(unique_id)
                    self.logger.info(
                        "Updated command mapping dictionary is: %s",
                        self.command_mapping,
                    )

                case (
                    ResultCode.REJECTED
                    | ResultCode.FAILED
                    | ResultCode.NOT_ALLOWED
                    | ResultCode.ABORTED
                ):
                    self.event_dict[self.command_id].update(
                        {dev_name: {"error": message}}
                    )
                    self.error_count += 1
                    self.command_mapping[self.command_id].remove(unique_id)
                    self.logger.info(
                        "Updated command mapping dictionary is: %s",
                        self.command_mapping,
                    )
                    self.logger.error(
                        "Exception occurred with value: %s for %s \
                            command_id for device: %s",
                        value,
                        self.command_id,
                        dev_name,
                    )
            if len(self.event_dict[self.command_id]) == 2:
                self.update_long_running_command_result_callback()
        except Exception as exception:
            self.logger.exception(
                "Exception occurred while processing"
                + "long running command result"
                + "attribute event: %s",
                exception,
            )

    def update_long_running_command_result_callback(self) -> None:
        """
        This method checks for errors after receiving events from
        all the desired devices. If there are errors it will
        aggregate them and update the lrcr callback.
        If there are no errors it will just reset the event dicitonary.
        """
        if self.error_count:
            # modify below message to include value from error_dict
            exception_message = "Exception occurred on the following devices: "
            for devname, data in self.event_dict[self.command_id].items():
                if isinstance(data, dict):
                    error_message = data["error"]
                    exception_message += (
                        f"{self.command_id}: {devname}: " + f"{error_message}"
                    )
            self.logger.info(
                "Updating LRCRCallback with following values: "
                + "command_id: %s, resultcode: %s, message: %s",
                self.command_id,
                ResultCode.FAILED,
                exception_message,
            )
            self.long_running_result_callback(
                self.command_id,
                ResultCode.FAILED,
                exception_msg=exception_message,
            )
            self.observable.notify_observers(attribute_value_change=True)
        self.reset_event_count(self.command_id)

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
        with self.lock:
            self.logger.debug(f"State event for {device_name}: {state}")
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
                    f"Updated State of {devInfo.dev_name}: {devInfo.state}"
                )
                devInfo.last_event_arrived = time.time()
                devInfo.update_unresponsive(False)
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

        with self.lock:
            new_state = self._telescope_state_aggregator.aggregate()
            self.component.telescope_state = new_state

    def _aggregate_health_state(self):
        """
        Aggregates all health states
        and call the relative callback if available
        """
        if self._health_state_aggregator is None:
            self._health_state_aggregator = HealthStateAggregatorLow(
                self, self.logger
            )

        with self.lock:
            self.component.telescope_health_state = (
                self._health_state_aggregator.aggregate()
            )
            self.logger.debug(
                "SubarrayNode aggregated healthState: "
                + f"{HealthState(self.component.telescope_health_state).name}"
            )

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

    def check_device_responsiveness(self, command_name) -> None:
        """
        This method overrides the method from super class
        to add responsive checks for the devices
        :param command_name: Command name for the check
        :type command_name: str
        """
        if command_name in self.supported_commands_for_responsive_check:
            self.logger.debug(f"Checking low devices for {command_name}")
            self.check_if_mccs_mln_is_responsive()
            self.check_if_subarrays_are_responsive()

    def update_telescope_availability(self, device_name, event_value):
        """Updates telescope availability"""
        with self.lock:
            self.logger.debug(f"device_name is: {device_name}")
            self.logger.debug(f"event_value is: {event_value}")

            if "tm_subarray_node" in device_name:
                self.subarray_availability[device_name] = event_value
            elif "tm_leaf_node/csp_master" in device_name:
                self.csp_mln_availability = event_value
            elif "tm_leaf_node/sdp_master" in device_name:
                self.sdp_mln_availability = event_value
            elif MCCS_MLN_SUFIX in device_name:
                self.mccs_mln_availability = event_value
            self._telescope_availability_aggregator.aggregate()

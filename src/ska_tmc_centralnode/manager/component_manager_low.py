"""
This module is inherited from CNComponentManager.

It is component Manager for Low Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import time

from ska_tmc_common.enum import LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from ska_tmc_centralnode.manager.aggregators import (
    HealthStateAggregatorLow,
    TelescopeAvailabilityAggregatorLow,
    TelescopeStateAggregatorLow,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager


class CNComponentManagerLow(CNComponentManager):
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
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
        skuid_service="",
        command_timeout=30,
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
            component_state_callback,
            _telescope_availability_callback,
            max_workers,
            proxy_timeout,
            sleep_time,
            skuid_service="",
            command_timeout=30,
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

        telescope_availability = self.get_telescope_availability()
        telescope_availability["tmc_subarrays"] = self.subarray_availability
        self.set_telescope_availability = telescope_availability

        self._telescope_availability_aggregator = (
            TelescopeAvailabilityAggregatorLow(self, self.logger)
        )

    def check_if_mccs_mln_is_responsive(self):
        self.logger.info("Checking if MCCSMasterLeafNode is responsive")
        return self._check_if_device_is_responsive(
            [self.input_parameter.mccs_mln_dev_name]
        )

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
        if command_name in ["TelescopeOn", "TelescopeOff", "TelescopeStandby"]:
            self.logger.debug(f"Checking low devices for {command_name}")
            self.check_if_mccs_mln_is_responsive()
            self.check_if_subarrays_are_responsive()
        elif command_name in ["AssignResources", "ReleaseResources"]:
            self.logger.debug(f"Checking low devices for {command_name}")
            self.check_if_subarrays_are_responsive()
            self.check_if_mccs_mln_is_responsive()

        return True

    def update_telescope_availability(self, device_name, event_value):
        with self.lock:
            self.logger.debug(f"device_name is: {device_name}")
            self.logger.debug(f"event_value is: {event_value}")

            if "tm_subarray_node" in device_name:
                self.subarray_availability[device_name] = event_value
            elif "tm_leaf_node/csp_master" in device_name:
                self.csp_mln_availability = event_value
            elif "tm_leaf_node/sdp_master" in device_name:
                self.sdp_mln_availability = event_value
            self._telescope_availability_aggregator.aggregate()

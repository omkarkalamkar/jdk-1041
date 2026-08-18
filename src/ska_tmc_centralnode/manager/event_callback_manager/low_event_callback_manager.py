"""Module to manage all Low telescope the change event callbacks.
"""
import threading
from logging import Logger
from typing import Callable

from ...manager.aggregators import TelescopeAvailabilityAggregatorLow
from ...model.component import TmcComponent
from ...model.input import InputParameterLow
from ..event_data_manager import EventDataManager
from .event_callback_manager import EventCallbackManager


class LowEventCallbackManager(EventCallbackManager):
    """Class to manage change event callbacks for Low telescope."""

    def __init__(
        self,
        logger: Logger,
        component: TmcComponent,
        command_completion_cond: threading.Condition,
        input_parameter: InputParameterLow,
        event_data_manager: EventDataManager,
        _aggregate_state: Callable,
        subarray_availability: dict,
        set_csp_mln_availability: Callable,
        set_sdp_mln_availability: Callable,
        set_mccs_mln_availability: Callable,
        get_telescope_availability_aggregator: Callable[
            [], TelescopeAvailabilityAggregatorLow
        ],
    ):
        super().__init__(
            logger,
            component,
            command_completion_cond,
            input_parameter,
            event_data_manager,
            _aggregate_state,
        )
        self.subarray_availability = subarray_availability
        self.set_csp_mln_availability = set_csp_mln_availability
        self.set_sdp_mln_availability = set_sdp_mln_availability
        self.set_mccs_mln_availability = set_mccs_mln_availability
        self.get_telescope_availability_aggregator = (
            get_telescope_availability_aggregator
        )

    def update_telescope_availability(self, device_name, event_value):
        """Updates telescope availability"""
        with self.rlock:
            self.logger.debug("Device name is: %s", device_name)
            self.logger.debug("Event value is: %s", event_value)

            if device_name in self.input_parameter.subarray_dev_names:
                self.subarray_availability[device_name] = event_value
            elif self.input_parameter.csp_mln_dev_name == device_name:
                self.set_csp_mln_availability(event_value)
            elif self.input_parameter.sdp_mln_dev_name == device_name:
                self.set_sdp_mln_availability(event_value)
            elif self.input_parameter.mccs_mln_dev_name == device_name:
                self.set_mccs_mln_availability(event_value)
            self.get_telescope_availability_aggregator().aggregate()

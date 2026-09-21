"""Module to manage all Low telescope the change event callbacks."""

from dataclasses import dataclass
from typing import Callable

from ...manager.aggregators import TelescopeAvailabilityAggregatorLow
from ...model.input import InputParameterLow
from .event_callback_manager import EventCallbackContext, EventCallbackManager


@dataclass
class LowEventCallbackContext(EventCallbackContext[InputParameterLow]):
    """Context to manage MID event callbacks.

    Attributes:
        update_subarray_availability: Callable to update subarray
        availability status.ict
        set_csp_mln_availability: Callable to set CSP Master Leaf Node
        availability.
        set_sdp_mln_availability: Callable to set SDP Master Leaf Node
        availability.
        set_mccs_mln_availability: Callable to set MCCS Master Leaf Node
        availability.
        _telescope_availability_aggregator: Instance of
        TelescopeAvailabilityAggregatorLow.
    """

    update_subarray_availability: Callable[[str, bool], None]
    set_csp_mln_availability: Callable[[bool], None]
    set_sdp_mln_availability: Callable[[bool], None]
    set_mccs_mln_availability: Callable[[bool], None]
    _telescope_availability_aggregator: TelescopeAvailabilityAggregatorLow


class LowEventCallbackManager(EventCallbackManager[InputParameterLow]):
    """Class to manage change event callbacks for Low telescope."""

    def __init__(
        self,
        context: LowEventCallbackContext,
    ):
        """Initialization of LowEventCallbackManager

        :param context: Instance of LowEventCallbackContext.
        :type logger: LowEventCallbackContext
        """
        super().__init__(context)
        self.update_subarray_availability = (
            context.update_subarray_availability
        )
        self.set_csp_mln_availability = context.set_csp_mln_availability
        self.set_sdp_mln_availability = context.set_sdp_mln_availability
        self.set_mccs_mln_availability = context.set_mccs_mln_availability
        self._telescope_availability_aggregator = (
            context._telescope_availability_aggregator
        )

    def update_telescope_availability(
        self, device_name: str, event_value: bool
    ) -> None:
        """Updates telescope availability"""
        with self.rlock:
            self.logger.debug("Device name is: %s", device_name)
            self.logger.debug("Event value is: %s", event_value)

            if device_name in self.input_parameter.subarray_dev_names:
                self.update_subarray_availability(device_name, event_value)
            elif self.input_parameter.csp_mln_dev_name == device_name:
                self.set_csp_mln_availability(event_value)
            elif self.input_parameter.sdp_mln_dev_name == device_name:
                self.set_sdp_mln_availability(event_value)
            elif self.input_parameter.mccs_mln_dev_name == device_name:
                self.set_mccs_mln_availability(event_value)
            self._telescope_availability_aggregator.aggregate()

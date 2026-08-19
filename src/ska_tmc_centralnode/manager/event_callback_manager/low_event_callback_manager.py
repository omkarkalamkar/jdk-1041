"""Module to manage all Low telescope the change event callbacks.
"""
import threading
from logging import Logger
from typing import Callable

from ...manager.aggregators import TelescopeAvailabilityAggregatorLow
from ...model.component import CentralComponent
from ...model.input import InputParameterLow
from ..event_data_manager import EventDataManager
from .event_callback_manager import EventCallbackManager


class LowEventCallbackManager(EventCallbackManager[InputParameterLow]):
    """Class to manage change event callbacks for Low telescope."""

    def __init__(
        self,
        logger: Logger,
        component: CentralComponent,
        command_completion_cond: threading.Condition,
        input_parameter: InputParameterLow,
        event_data_manager: EventDataManager,
        _aggregate_state: Callable[[], None],
        subarray_availability: dict[str, bool],
        set_csp_mln_availability: Callable[[bool], None],
        set_sdp_mln_availability: Callable[[bool], None],
        set_mccs_mln_availability: Callable[[bool], None],
        _telescope_availability_aggregator: TelescopeAvailabilityAggregatorLow,
    ):
        """Initialization of LowEventCallbackManager

        :param logger: Instance of Logger.
        :type logger: Logger
        :param component: instance of CentralComponent.
        :type component: TmcComponent
        :param command_completion_cond: completion condition.
        :type command_completion_cond: threading.Condition
        :param input_parameter: Instance of InputParameter.
        :type input_parameter: Union[InputParameterMid, InputParameterLow]
        :param event_data_manager: Instance of EventDataManager
        :type event_data_manager: EventDataManager
        :param _aggregate_state: Callable to aggregate states.
        :type _aggregate_state:  Callable[[],None]
        :param subarray_availability: Dictionary with subarray
        availability status.
        :type subarray_availability: dict
        :param set_csp_mln_availability: Callable to set CSP Master Leaf Node
        availability.
        :type set_csp_mln_availability: Callable[[bool],None]
        :param set_sdp_mln_availability: Callable to set SDP Master Leaf Node
        availability.
        :type set_sdp_mln_availability: Callable[[bool],None]
        :param set_mccs_mln_availability: Callable to set MCCS Master Leaf Node
        availability.
        :type set_mccs_mln_availability: Callable[[bool],None]
        :param _telescope_availability_aggregator: Instance of
        TelescopeAvailabilityAggregatorLow.
        :type _telescope_availability_aggregator:
        TelescopeAvailabilityAggregatorLow.
        """
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
        self._telescope_availability_aggregator = (
            _telescope_availability_aggregator
        )

    def update_telescope_availability(
        self, device_name: str, event_value: bool
    ) -> None:
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
            self._telescope_availability_aggregator.aggregate()

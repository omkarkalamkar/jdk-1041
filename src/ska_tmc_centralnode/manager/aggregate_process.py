"""
This module contain process for aggregation
"""
import logging
from multiprocessing import Event, Queue

from ska_control_model import HealthState
from ska_ser_logging import configure_logging
from ska_tmc_common.v1.aggregate_process import AggregationProcess
from ska_tmc_common.v1.aggregators import StateAggregator

from ska_tmc_centralnode.manager.transition_rules.health_state_rules import (
    HEALTH_STATE_RULES,
    HEALTH_STATE_RULES_MID,
)

configure_logging("DEBUG")

LOGGER = logging.getLogger(__name__)


class HealthAggregatorFactory:
    """Factory class to return the appropriate
    HealthStateAggregator instance."""

    @staticmethod
    def get_aggregator(telescope: str):
        """Static method to return aggregator class instance"""
        if telescope == "mid":
            return StateAggregator(HealthState, HEALTH_STATE_RULES_MID)
        if telescope == "low":
            return StateAggregator(HealthState, HEALTH_STATE_RULES)
        raise ValueError(f"Unknown telescope type: {telescope}")


class HealthStateAggregationProcessor(AggregationProcess):
    """
    Health State Aggregation Processor

    Inherits from AggregationProcess and implements health-specific
    state aggregation logic.
    """

    def __init__(
        self,
        event_data_queue: Queue,
        aggregated_health_state: list,
        aggregate_update_event: Event,
        telescope: str = "mid",
        callback=None,
    ):
        self.telescope = telescope
        super().__init__(
            event_data_queue,
            aggregated_health_state,
            aggregate_update_event,
            callback,
        )

    def _convert_event_data_to_dict_for_rule_engine(self, event_data):
        """Extract relevant fields from event data into a dictionary."""
        event_data_dict = {
            "all_unique_health_states": list(
                set(
                    health_data.health_state
                    for health_data in event_data.health_state_data.values()
                )
            ),
            "all_unique_admin_modes": list(
                set(
                    admin_mode.admin_mode
                    for admin_mode in event_data.admin_mode_data.values()
                )
            ),
        }
        return event_data_dict

    def set_state_aggregator(self):
        """Return an instance of HealthStateAggregator
        for the given telescope."""
        return HealthAggregatorFactory.get_aggregator(self.telescope)

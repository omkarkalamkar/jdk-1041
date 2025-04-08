"""
This module contains the process for aggregation.
"""
import logging
import queue
from dataclasses import asdict
from multiprocessing import Event, Process, Queue

from ska_ser_logging import configure_logging

from ska_tmc_centralnode.manager.aggregators import HealthStateAggregator

configure_logging("DEBUG")

LOGGER = logging.getLogger(__name__)


class HealthAggregatorFactory:
    """Factory class to return the appropriate
    HealthStateAggregator instance."""

    @staticmethod
    def get_aggregator(telescope: str):
        """Static method to return aggregator class instance"""
        if telescope == "mid":
            return HealthStateAggregator()
        if telescope == "low":
            return HealthStateAggregator()

        raise ValueError(f"Unknown telescope type: {telescope}")


class HealthStateAggregationProcessor:
    """Health State Aggregation Process Class"""

    def __init__(
        self,
        event_data_queue: Queue,
        aggregated_health_state,
        aggregate_update_event,
        telescope="mid",
        callback=None,
    ):
        """
        :param event_data_queue: Queue to track event data
        :type event_data_queue: multiprocessing Queue
        :param aggregated_health_state: Shared variable that holds the
        aggregated health state
        :type aggregated_health_state: list
        :param aggregate_update_event: Event to signal health state update
        :param telescope: Type of telescope ("mid" or "low")
        :param callback: Optional callback method invoked
        when health state updates
        """
        self.event_data_queue = event_data_queue
        self.aggregated_health_state = aggregated_health_state
        self.aggregate_update_event = aggregate_update_event
        self.callback = callback

        # Use factory to get the appropriate aggregator
        self.health_state_aggregator = HealthAggregatorFactory.get_aggregator(
            telescope
        )

        self.aggregation_process = Process(
            target=self.run_aggregation_process,
            name="healthstate_aggregation_process",
            args=(self.health_state_aggregator,),
        )
        self.aggregation_process_alive_event = Event()

    def run_aggregation_process(self, aggregator):
        """Runs the health state aggregation process."""
        LOGGER.info(
            "Health state aggregation process started with process id %s",
            self.aggregation_process.pid,
        )

        while not self.aggregation_process_alive_event.is_set():
            try:
                event_data = self.event_data_queue.get(block=True, timeout=0.1)
                event_data_dict = self._convert_event_data_to_dict(event_data)
                event_data_dict["event_data"] = asdict(event_data)

                self.aggregated_health_state[0] = aggregator.aggregate(
                    event_data_dict
                )
                self.aggregate_update_event.set()

                if self.callback:
                    self.callback(self.aggregated_health_state[0])

                LOGGER.info(
                    "Aggregated HealthState %s", self.aggregated_health_state
                )
            except queue.Empty:
                pass

    def _convert_event_data_to_dict(self, event_data) -> dict:
        """Extract necessary data from event and create
        a dictionary for aggregation."""
        event_data_dict = {
            "all_unique_health_states": list(
                set(
                    health_data.health_state
                    for health_data in event_data.health_state_data.values()
                )
            )
        }
        return event_data_dict

    def start_aggregation_process(self):
        """Start the health state aggregation process."""
        LOGGER.debug("Starting health state aggregation process")
        self.aggregation_process.start()

    def stop_aggregation_process(self):
        """Stop the running health state aggregation process."""
        LOGGER.debug("Stopping health state aggregation process")
        if self.aggregation_process.is_alive():
            self.aggregation_process_alive_event.set()
            self.aggregation_process.join()
        LOGGER.debug("Health state aggregation process stopped.")

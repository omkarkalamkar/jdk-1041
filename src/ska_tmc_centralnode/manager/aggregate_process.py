import logging
import queue
from dataclasses import asdict
from multiprocessing import Event, Process, Queue

from ska_ser_logging import configure_logging
from ska_tmc_subarraynode.manager.aggregators import HealthStateAggregatorLow

configure_logging("DEBUG")

LOGGER = logging.getLogger(__name__)


class HealthStateAggregationProcess:
    """Health State Aggregation Process Class"""

    def __init__(
        self,
        event_data_queue: Queue,
        aggregated_health_state,
        aggregate_update_event,
        callback=None,
    ):
        """
        :param event_data_queue: Queue to track event data
        :type event_data_queue: multiprocessing queue
        :param aggregated_health_state: Aggregated health state
        updated after aggregation
        This is a shared variable between processes
        :type aggregated_health_state: list
        :param callback: Callback method reference used when
        aggregated health state is updated
        """
        self.health_state_aggregator = HealthStateAggregatorLow()
        self.event_data_queue = event_data_queue
        self.aggregated_health_state = aggregated_health_state
        self.callback = callback
        self.aggregate_update_event = aggregate_update_event
        self.aggregation_process = Process(
            target=self.run_aggregation_process,
            name="healthstate_aggregation_process",
        )
        self.aggregation_process_alive_event = Event()

    def run_aggregation_process(self):
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

                self.aggregated_health_state[
                    0
                ] = self.health_state_aggregator.aggregate(event_data_dict)
                self.aggregate_update_event.set()

                if self.callback:
                    self.callback(self.aggregated_health_state[0])

                LOGGER.info(
                    "Aggregated HealthState %s", self.aggregated_health_state
                )
            except queue.Empty:
                pass

    def _convert_event_data_to_dict(self, event_data) -> dict:
        """Extract necessary data from event and create a
        dictionary for aggregation."""
        event_data_dict = {}
        all_health_states = [
            health_data.health_state
            for device, health_data in event_data.health_state_data.items()
        ]
        event_data_dict["all_unique_health_states"] = list(
            set(all_health_states)
        )

        # event_data_dict["command_in_progress"] = event_data.command_in_progress
        # event_data_dict["command_timestamp"] = event_data.command_timestamp

        return event_data_dict

    def start_aggregation_process(self):
        """Start the health state aggregation process."""
        self.aggregation_process.start()

    def stop_aggregation_process(self):
        """Stop the running health state aggregation process."""
        LOGGER.debug("Stopping health state aggregation process")
        if self.aggregation_process.is_alive():
            self.aggregation_process_alive_event.set()
            self.aggregation_process.join()
        LOGGER.debug("Health state aggregation process stopped")

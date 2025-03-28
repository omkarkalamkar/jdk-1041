import functools
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ska_control_model import HealthState
from ska_ser_logging import configure_logging

configure_logging("DEBUG")
LOGGER = logging.getLogger(__name__)


@dataclass
class HealthStateData:
    """
    DataClass for HealthState and its Timestamp.
    """

    health_state: HealthState
    event_timestamp: datetime


@dataclass
class EventDataStorage:
    """
    A class to store the Events received for HealthState attribute.
    """

    health_state_data: dict = field(default_factory=dict)


def pre_process(func: Callable) -> Callable:
    """Decorator for preprocessing event data"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        """Wrapper method for pre-process decorator"""
        try:
            data_type = kwargs.get("data_type")
            device = kwargs.get("device", "").lower()
            received_timestamp = kwargs.get("received_timestamp")

            LOGGER.debug(
                "Processing function: %s for HealthState data", func.__name__
            )
            target_dict = self.event_info.health_state_data

            if device in target_dict:
                if self.compare_timevals(
                    target_dict[device].event_timestamp,
                    received_timestamp,
                ):
                    func(self, *args, **kwargs)
                else:
                    LOGGER.info("Received stale event")
            else:
                func(self, *args, **kwargs)
        except Exception as exception:
            LOGGER.exception("Preprocessing failed: %s", exception)

    return wrapper


class EventDataManager:
    """
    A class to update the values of HealthState events received
    in EventDataStorage class.
    """

    def __init__(self, component_manager):
        self.event_info = EventDataStorage()
        self.component_manager = component_manager
        self.eventlock = threading.RLock()

    def compare_timevals(
        self, current_timestamp: datetime, received_timestamp: datetime
    ) -> bool:
        """Compare event timestamps to filter out stale events."""
        if received_timestamp is None:
            return False
        return current_timestamp < received_timestamp

    @pre_process
    def update_event_data(
        self,
        device: str,
        data: str,
        data_type: str,
        received_timestamp: datetime = None,
    ):
        """Update HealthState data in the EventDataStorage class."""
        device_name = device.lower()
        with self.eventlock:
            self.event_info.health_state_data[device_name] = HealthStateData(
                health_state=data, event_timestamp=received_timestamp
            )
            LOGGER.info(
                "Updated HealthState - %s",
                self.event_info.health_state_data[device_name],
            )

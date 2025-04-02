"""
Use event manager to manage all event related data
"""
import copy
import functools
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict

from ska_ser_logging import configure_logging
from ska_tango_base.control_model import HealthState

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
    A class to store the Events received for different attributes.
    """

    health_state_data: dict = field(default_factory=dict)


def pre_process(func: Callable) -> Callable:
    """Decorator for preprocessing event data"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        """wrapper method for pre process decorator"""

        try:
            data_type = kwargs.get("data_type")
            dict_name = self.attribute_mapping.get(data_type)
            device = kwargs.get("device", "").lower()
            received_timestamp = kwargs.get("received_timestamp")

            LOGGER.debug(
                "Processing function: %s with target dict:%s",
                func.__name__,
                dict_name,
            )
            target_dict = getattr(self.event_info, dict_name)

            match dict_name:
                case "health_state_data":
                    if device in target_dict:
                        if self.compare_timevals(
                            target_dict[device].event_timestamp,
                            received_timestamp,
                        ):
                            func(self, *args, **kwargs)
                            self.update_aggragation_queue()
                        else:
                            LOGGER.info("Received stale event")
                    else:
                        func(self, *args, **kwargs)
                        self.update_aggragation_queue()

                case _:
                    LOGGER.debug("Invalid Dictionary name for EventData")
        except Exception as exception:
            log_msg = (
                "Preprocessing failed for  attribute %s: with exception %s",
                data_type,
                exception,
            )
            LOGGER.exception(log_msg)

    return wrapper


class EventDataManager:
    """
    A class to update the values of events received for different
     attributes in EventDataStorage class
    """

    def __init__(self, component_manager):
        self.event_info = EventDataStorage()
        self.component_manager = component_manager

        self.attribute_mapping: Dict[str, str] = {
            "HealthState": "health_state_data",
        }

        self.eventlock = threading._RLock()

    def get_enum_name_from_value(self, enum_class, value):
        """
        Get the name from value of enum
        """
        for name, member in enum_class.__members__.items():
            if member.value == value:
                return name
        return None

    def compare_timevals(
        self, current_timestamp: datetime, received_timestamp: datetime
    ):
        """
        A method to compare the timestamps of events received with the
         existing timestamp.
        """

        LOGGER.info(
            "current_timestamp is  %s and received_timestamp is %s",
            current_timestamp,
            received_timestamp,
        )

        if received_timestamp is None:
            return False
        if current_timestamp < received_timestamp:
            return True
        return False

    def update_aggragation_queue(self):
        """
        A method to put a copy of the EventDataStorage object whenever
         it receives an event.
        """
        with self.component_manager.process_lock:
            current_event_info = copy.deepcopy(self.event_info)
            LOGGER.info("event_info objects contents  %s", self.event_info)
            self.component_manager.event_data_queue.put(current_event_info)

        LOGGER.info("Lock released from update_aggragation_queue ")

    @pre_process
    def update_event_data(
        self,
        device: str,
        data: HealthState,
        data_type: str,
        received_timestamp: datetime = None,
    ):
        """
        A method to receive and update device name, data, and timestamp in the
        EventDataStorage Class
        """
        device_name = device.lower()
        with self.eventlock:
            dict_name = self.attribute_mapping.get(data_type)
            target_dict = getattr(self.event_info, dict_name)

            if data_type == "HealthState":
                data = self.get_enum_name_from_value(HealthState, int(data))
                target_dict[device_name] = HealthStateData(
                    health_state=data, event_timestamp=received_timestamp
                )
                LOGGER.info("HealthState - %s", target_dict[device_name])

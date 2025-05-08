"""
Use event manager to manage all event related data
"""
import copy
import functools
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, Union

from ska_ser_logging import configure_logging
from ska_tango_base.control_model import AdminMode, HealthState

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
class AdminModeData:
    """
    DataClass for AdminMode and its Timestamp
    """

    admin_mode: AdminMode
    event_timestamp: datetime


@dataclass
class EventDataStorage:
    """
    A class to store the Events received for different attributes.
    """

    health_state_data: dict = field(default_factory=dict)
    admin_mode_data: dict = field(default_factory=dict)


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
                case "health_state_data" | "admin_mode_data":
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
            "AdminMode": "admin_mode_data",
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
            table_lines = ["EventDataStorage:"]

            # Define headers for the table
            headers = ["Device", "StateType", "State", "Timestamp"]
            col_widths = {
                "Device": len(headers[0]),
                "StateType": len(headers[1]),
                "State": len(headers[2]),
                "Timestamp": len(headers[3]),
            }
            data_entries = []

            def format_timestamp(timestamp):
                return timestamp.isoformat() + "Z" if timestamp else "None"

            def update_col_widths(dev, state_type, state_str, timestamp_str):
                col_widths["Device"] = max(col_widths["Device"], len(str(dev)))
                col_widths["StateType"] = max(
                    col_widths["StateType"], len(str(state_type))
                )
                col_widths["State"] = max(
                    col_widths["State"], len(str(state_str))
                )
                col_widths["Timestamp"] = max(
                    col_widths["Timestamp"], len(str(timestamp_str))
                )

            for dev, data in self.event_info.health_state_data.items():
                timestamp_str = format_timestamp(data.event_timestamp)
                state_str = str(data.health_state)
                data_entries.append(
                    (dev, "HealthState", state_str, timestamp_str)
                )
                update_col_widths(dev, "HealthState", state_str, timestamp_str)

            for dev, data in self.event_info.admin_mode_data.items():
                timestamp_str = format_timestamp(data.event_timestamp)
                state_str = str(data.admin_mode)
                data_entries.append(
                    (dev, "AdminMode", state_str, timestamp_str)
                )
                update_col_widths(dev, "AdminMode", state_str, timestamp_str)

            data_entries.sort(key=lambda x: x[0])

            table_lines.append(
                f"  {headers[0]:<{col_widths['Device']}} "
                f"{headers[1]:<{col_widths['StateType']}} "
                f"{headers[2]:<{col_widths['State']}} "
                f"{headers[3]:<{col_widths['Timestamp']}}"
            )

            for dev, state_type, state, timestamp in data_entries:
                table_lines.append(
                    f"  {str(dev):<{col_widths['Device']}} "
                    f"{str(state_type):<{col_widths['StateType']}} "
                    f"{str(state):<{col_widths['State']}} "
                    f"{str(timestamp):<{col_widths['Timestamp']}}"
                )

            LOGGER.info("\n".join(table_lines))
            LOGGER.info("event_info objects contents  %s", self.event_info)
            self.component_manager.event_data_queue.put(current_event_info)

        LOGGER.info("Lock released from update_aggragation_queue ")

    @pre_process
    def update_event_data(
        self,
        device: str,
        data: Union[HealthState, AdminMode],
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

            elif data_type == "AdminMode":
                data = self.get_enum_name_from_value(AdminMode, int(data))
                target_dict[device_name] = AdminModeData(
                    admin_mode=data, event_timestamp=received_timestamp
                )
                LOGGER.info("AdminMode - %s", target_dict[device_name])

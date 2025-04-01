"""
Use event manager to manager all event related data
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


# @dataclass
# class CommandResultData:
#     """
#     DataClass for longrunningcommandresult and its timestamp.
#     """

#     result: str
#     unique_id: str
#     event_timestamp: datetime


# @dataclass
# class PointingStateData:
#     """
#     DataClass for PointingState and its timestamp.
#     """

#     pointing_state: PointingState
#     event_timestamp: datetime


# @dataclass
# class DishModeData:
#     """
#     DataClass for DishMode and its timestamp.
#     """

#     dish_mode: DishMode
#     event_timestamp: datetime


@dataclass
class EventDataStorage:
    """
    A class to store the Events received for different attributes.
    """

    health_state_data: dict = field(default_factory=dict)
    # command_result_data: dict = field(default_factory=dict)
    # dish_mode_data: dict = field(default_factory=dict)
    # pointing_state_data: dict = field(default_factory=dict)
    # command_timestamp: datetime = None
    # command_in_progress: str = ""
    # is_partial_configuration: bool = False
    # is_mapping_scan: bool = False


def pre_process(func: Callable) -> Callable:
    """Decorator for preprocessing event data"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        """wrapper method for pre process decorator"""

        # def is_unknown(data):
        #     try:
        #         if isinstance(data[1], str):
        #             result_code = json.loads(data[1])
        #             if result_code[0] == ResultCode.UNKNOWN:
        #                 LOGGER.info("UNKNOWN result code found")
        #                 return True
        #     except IndexError:
        #         LOGGER.exception("Exception while checking unknown")
        #     return False

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

                # case "command_result_data":
                #     LOGGER.debug("Performing actions for command_result_data")

                #     data = kwargs.get("data")
                #     unique_id = data[0]

                #     LOGGER.debug(
                #         "Received LongRunningCommandResult data - %s"
                #         " for device - %s",
                #         unique_id,
                #         device,
                #     )

                #     if device in target_dict:
                #         if target_dict[device].unique_id[0] == unique_id[0]:
                #             if not is_unknown(data):
                #                 func(self, *args, **kwargs)
                #                 self.update_aggragation_queue()
                #         else:
                #             LOGGER.info(
                #                 "LongRunningCommandResult Id not registered"
                #             )
                #     else:
                #         if isinstance(unique_id[0], list):
                #             # Handle case where unique_id[0] is a list
                #             ends_with_on_or_off = any(
                #                 uid.endswith("On") or uid.endswith("Off")
                #                 for uid in unique_id[0]
                #             )
                #         else:
                #             # Handle case where unique_id[0] is a single value
                #             ends_with_on_or_off = unique_id[0].endswith(
                #                 "On"
                #             ) or unique_id[0].endswith("Off")

                #         if not ends_with_on_or_off:
                #             func(self, *args, **kwargs)
                #             LOGGER.debug(
                #                 "Updating unique_id %s in target_dict",
                #                 unique_id,
                #             )
                #             self.update_aggragation_queue()

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

    # def clear_lrcr(self):
    #     """clears LongRunning Command Results"""
    #     LOGGER.info("Clearing command results from event info")
    #     self.event_info.command_result_data.clear()

    # def clear_dish_data(self):
    #     """clear dish data from event info"""
    #     self.event_info.dish_mode_data.clear()
    #     self.event_info.pointing_state_data.clear()

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
            # It should be a deep copy not direct object
            # self.event_info.is_partial_configuration = (
            #     self.component_manager.is_partial_configuration
            # )
            # self.event_info.command_in_progress = (
            #     self.component_manager.command_in_progress
            # )
            # self.event_info.command_timestamp = (
            #     self.component_manager.command_timestamp
            # )
            # self.event_info.is_mapping_scan = (
            #     self.component_manager.is_mapping_scan
            # )
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
                    obs_state=data, event_timestamp=received_timestamp
                )
                LOGGER.info("ObsState - %s", target_dict[device_name])

"""Event manager class for CentralNode"""

import logging
from typing import Callable, Optional

import tango
from ska_ser_logging import configure_logging
from ska_tmc_common.v2.event_manager import EventManager

configure_logging("DEBUG")

LOGGER = logging.getLogger(__name__)


class CentralNodeEventManager(EventManager):
    """
    CentralNodeEventManager class inherits from EventManager and
    adds event callbacks.
    """

    def __init__(
        self,
        component_manager,
        subscription_configuration: Optional[dict[str, list]] = None,
        logger: logging.Logger = LOGGER,
        stateless: bool = True,
        event_subscription_check_period: int = 1,
        event_error_max_count: int = 10,
        status_update_callback: Optional[Callable] = None,
        maximum_status_queue_size: int = 50,
    ) -> None:
        super().__init__(
            component_manager,
            subscription_configuration,
            logger,
            stateless,
            event_subscription_check_period,
            event_error_max_count,
            status_update_callback,
            maximum_status_queue_size,
        )

        self._component_manager = component_manager
        self.logger = logger

    def cspcontrolleradminmode_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        It handles the adminMode events of csp controller device.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues["adminMode"].put(
            event
        )

    def sdpcontrolleradminmode_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        It handles the adminMode events of sdp controller device.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues["adminMode"].put(
            event
        )

    def mccscontrolleradminmode_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        It handles the adminMode events of mccs controller device.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues["adminMode"].put(
            event
        )

    def healthstate_event_callback(self, event: tango.EventData) -> None:
        """
        It handles the health state events of subsystem's
        controller and subarray devices.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues[
            "healthState"
        ].put(event)

    def adminmode_event_callback(self, event: tango.EventData) -> None:
        """
        It handles the admin mode events of subsystem's
        controller and subaray devices.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues["adminMode"].put(
            event
        )

    def state_event_callback(self, event: tango.EventData) -> None:
        """
        It handles the state events of subsystem's
        controller and subaray devices.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues["state"].put(
            event
        )

    def assignedresources_event_callback(self, event: tango.EventData) -> None:
        """
        Handles assigned Resources event.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues[
            "assignedResources"
        ].put(event)

    def obsstate_event_callback(self, event: tango.EventData) -> None:
        """
        Handles observation state event.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues["obsState"].put(
            event
        )

    def dishmode_event_callback(self, event: tango.EventData) -> None:
        """
        Method to handle and update the latest
        value of dishMode attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues["dishMode"].put(
            event
        )

    def kvaluevalidationresult_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        Method to handle kValueValidationResult from dish
        leaf node.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues[
            "kValueValidationResult"
        ].put(event)

    def dishvccmapvalidationresult_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        Handle DishVccMapValidationResult change event.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues[
            "DishVccMapValidationResult"
        ].put(event)

    def issubsystemavailable_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        Method to handle and update the latest value of isSubsystemAvailable
        attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues[
            "isSubsystemAvailable"
        ].put(event)

    def issubarrayavailable_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        Method to handle and update the latest value of isSubarrayAvailable
        attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues[
            "isSubarrayAvailable"
        ].put(event)

    def gpmversion_event_callback(self, event: tango.EventData) -> None:
        """
        Handle GPM version change event.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_processor.event_queues["gpmVersion"].put(
            event
        )

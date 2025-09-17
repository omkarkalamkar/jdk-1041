"""Event manager class for CentralNode"""

import logging
import re
from typing import Callable, Optional

import tango
from ska_ser_logging import configure_logging
from ska_tmc_common.v2.event_manager import EventManager

from ska_tmc_centralnode.utils.constants import MID_CSP_MLN_DEVICE

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

    def cspcontrolleradminmode_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        It handles the adminMode events of csp controller device.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["adminMode"].put(event)

    def sdpcontrolleradminmode_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        It handles the adminMode events of sdp controller device.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["adminMode"].put(event)

    def mccscontrolleradminmode_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        It handles the adminMode events of mccs controller device.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["adminMode"].put(event)

    def healthstate_event_callback(self, event: tango.EventData) -> None:
        """
        It handles the health state events of subsystem's
        controller and subarray devices.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["healthState"].put(event)

    def adminmode_event_callback(self, event: tango.EventData) -> None:
        """
        It handles the admin mode events of subsystem's
        controller and subaray devices.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["adminMode"].put(event)

    def state_event_callback(self, event: tango.EventData) -> None:
        """
        It handles the state events of subsystem's
        controller and subaray devices.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["state"].put(event)

    def assignedresources_event_callback(self, event: tango.EventData) -> None:
        """
        Handles assigned Resources event.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["assignedResources"].put(event)

    def obsstate_event_callback(self, event: tango.EventData) -> None:
        """
        Handles observation state event.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["obsState"].put(event)

    def dishmode_event_callback(self, event: tango.EventData) -> None:
        """
        Method to handle and update the latest
        value of dishMode attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["dishMode"].put(event)

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
        self._component_manager.event_queue["kValueValidationResult"].put(
            event
        )

    def dishvccmapvalidationresult_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        Handle DishVccMapValidationResult change event.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["DishVccMapValidationResult"].put(
            event
        )

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
        self._component_manager.event_queue["isSubsystemAvailable"].put(event)

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
        self._component_manager.event_queue["isSubarrayAvailable"].put(event)

    def longrunningcommandresult_event_callback(
        self, event: tango.EventData
    ) -> None:
        """
        Callback for longRunningCommandResult attribute.

        Delegates to specific handlers based on device type.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        if MID_CSP_MLN_DEVICE in event.attr_name:
            self._handle_load_dish_cfg_result_callback(event)
        elif (
            re.search(r"/(ska\d{3}|mkt\d{3})", event.attr_name, re.IGNORECASE)
            and self._component_manager.command_in_progress
            == "SetGlobalPointingModel"
        ):
            self._handle_set_gpm_result_callback(event)
        else:
            self._component_manager.event_queue[
                "longRunningCommandResult"
            ].put(event)

    def _handle_load_dish_cfg_result_callback(
        self, event: tango.EventData
    ) -> None:
        """
        Special handler for LoadDishCfg and SetKValue result events.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        if getattr(event, "attr_value", False):
            self._component_manager.event_queue["loadDishConfigResult"].put(
                event
            )
        elif getattr(event, "argout", False):
            self._component_manager.event_queue[
                "loadDishConfigResultAsync"
            ].put(event)

    def _handle_set_gpm_result_callback(self, event: tango.EventData) -> None:
        """
        Special handler for SetGPM result events.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["setGPMResult"].put(event)

    def gpmversion_event_callback(self, event: tango.EventData) -> None:
        """
        Handle GPM version change event.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
                change in event.

        """
        self._component_manager.event_queue["gpmVersion"].put(event)

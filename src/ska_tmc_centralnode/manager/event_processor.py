"""
EventProcessor encapsulates event queue management and worker thread
dispatch for CentralNodeComponentManager.
"""
import threading
from logging import Logger
from queue import Empty, Queue
from typing import Callable, Dict

import tango
from tango.utils import PyTangoThread


class EventProcessor:
    """Manages event queues, worker threads, and event dispatch.

    Each attribute has a dedicated Queue and a dedicated daemon thread
    that consumes from it.  Handlers are registered per attribute name
    and called with (device_name, value, timestamp) for every valid event.
    """

    _ATTRIBUTES = [
        "obsState",
        "assignedResources",
        "healthState",
        "adminMode",
        "isSubsystemAvailable",
        "isSubarrayAvailable",
        "state",
    ]

    def __init__(
        self,
        stop_event: threading.Event,
        logger: Logger,
        on_error: Callable[[str], None],
    ) -> None:
        """Initialize EventProcessor.

        Args:
            stop_event: Shared event that signals worker threads to exit.
            logger: Logger instance.
            on_error: Callback invoked with device_name when a Tango event
                carries an error flag (maps to update_event_failure on the
                component manager).
        """
        self._stop_event = stop_event
        self.logger = logger
        self._on_error = on_error
        attributes: list = self._get_attributes()
        self.event_queues: Dict[str, Queue] = {
            attr: Queue() for attr in attributes
        }
        self._handlers: Dict[str, Callable] = {}

    def _get_attributes(self) -> list:
        """Provides list of attributes to be processed.

        :return: List of attributes to be processed
        :rtype: list
        """
        return self._ATTRIBUTES

    def register_handler(self, attribute: str, handler: Callable) -> None:
        """Register a handler for the given attribute.

        Args:
            attribute: Attribute name matching a key in event_queues.
            handler: Callable invoked as
                ``handler(device_name, value, timestamp)``.
        """
        self._handlers[attribute] = handler

    def start(self) -> None:
        """Start one daemon worker thread per event queue."""
        for attribute in self.event_queues:
            PyTangoThread(
                target=self._process_event,
                args=[attribute],
                name=attribute,
                daemon=True,
            ).start()

    def _check_event_error(
        self, event: tango.EventData, callback: str
    ) -> bool:
        """Validate a Tango event and fire the error callback if needed.

        Args:
            event: The Tango event data object.
            callback: Label used in error log messages.

        Returns:
            True if the event carries an error, False otherwise.
        """
        if event.err:
            error = event.errors[0]
            self.logger.error(
                "Error occurred on %s for device: %s: %s , %s",
                callback,
                event.device.dev_name(),
                error.reason,
                error.desc,
            )
            self._on_error(event.device.dev_name())
            return True
        return False

    def _validate_event_structure(
        self, attribute_name: str, event_data: tango.EventData
    ) -> bool:
        """Validates event structure.

        :param event_data: Change Event data
        :type event_data:  tango.EventData
        :param attribute_name: Attribute name
        :type attribute_name: str
        :return: Returns False if the validation fails, else True.
        :rtype: bool
        """
        if not hasattr(event_data, "device") or not hasattr(
            event_data, "attr_value"
        ):
            self.logger.error(
                "Invalid event data structure for " f"{attribute_name}"
            )
            return False
        return True

    def _process_event(self, attribute_name: str) -> None:
        """Consume events from the queue and dispatch to the
            registered handler.

        Args:
            attribute_name: The attribute whose queue to consume.
        """
        while not self._stop_event.is_set():
            try:
                event_data = self.event_queues[attribute_name].get(
                    block=True, timeout=0.1
                )
                if self._check_event_error(
                    event_data, f"{attribute_name}_Callback"
                ):
                    continue
                if not self._validate_event_structure(
                    attribute_name, event_data
                ):
                    continue
                handler = self._handlers.get(attribute_name)
                if not handler:
                    continue
                if attribute_name in ("healthState", "adminMode"):
                    handler(
                        event_data.device.dev_name(),
                        event_data.attr_value.value,
                        event_data.attr_value.time.todatetime(),
                    )
                else:
                    handler(
                        event_data.device.dev_name(),
                        event_data.attr_value.value,
                    )
            except Empty:
                pass
            except Exception as exception:
                self.logger.error("%s", str(exception))
        self.logger.debug("Process event thread stopped")


class MidEventProcessor(EventProcessor):
    """Manages event queues, worker threads, and event dispatch
    specific to MID telescope.
    """

    _ATTRIBUTES_MID = [
        "dishMode",
        "kValueValidationResult",
        "DishVccMapValidationResult",
        "gpmVersion",
    ]

    def _get_attributes(self) -> list[str]:
        """Provides list of attributes to be processed for MID telescope.

        :return: List of attributes to be processed for MID telescope
        :rtype: list
        """
        attribute_list: list = super()._get_attributes()
        attribute_list.extend(self._ATTRIBUTES_MID)
        return attribute_list

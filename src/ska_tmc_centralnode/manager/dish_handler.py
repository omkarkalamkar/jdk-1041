"""_summary_"""
import tango


class DishHandler:
    """_summary_"""

    def __init__(
        self,
        component_manager,
        logger=None,
    ):
        """_summary_

        Args:
            component_manager (_type_): _description_
            logger (_type_, optional): _description_. Defaults to None.
        """
        self.component_manager = component_manager
        self.logger = logger

    def handle_dish_mode_event(self, event: tango.EventData) -> None:
        """Method to handle and update the latest value of dishMode
        attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self.logger.info("dish mode event %s", event)
        self.component_manager.event_queues["dishMode"].put(event)
        self.logger.info("callback exited")

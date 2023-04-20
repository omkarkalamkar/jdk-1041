import tango
from ska_tmc_common.event_receiver import EventReceiver


class CentralNodeEventReceiver(EventReceiver):
    """
    The CentralNodeEventReceiver class has the responsibility to receive events
    from the sub devices managed by the Central node.

    # The ComponentManager uses the handle events methods
    # for the attribute of interest.
    # For each of them a callback is defined.
    """

    def __init__(
        self,
        component_manager,
        logger=None,
        max_workers=1,
        proxy_timeout=500,
        sleep_time=1,
    ):
        super().__init__(
            component_manager, logger, max_workers, proxy_timeout, sleep_time
        )
        self._component_manager = component_manager

    def subscribe_events(self, dev_info):
        super().subscribe_events(dev_info)
        try:
            proxy = self._dev_factory.get_device(dev_info.dev_name)
            if ("subarray" in dev_info.dev_name) and (
                "leaf" not in dev_info.dev_name
            ):
                proxy.subscribe_event(
                    "assignedResources",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_assigned_resource_event,
                    stateless=True,
                )
            if "dish/master" in dev_info.dev_name:
                proxy.subscribe_events(
                    "dishMode",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_dish_mode_event,
                    stateless=True,
                )

        except Exception as e:
            self._logger.debug(
                "event not working for device %s/%s", proxy.dev_name, e
            )

    def handle_assigned_resource_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error(
                "Received error from device %s: %s %s",
                evt.device.dev_name(),
                error.reason,
                error.desc,
            )
            self._component_manager.update_event_failure(evt.device.dev_name())
            return

        new_value = evt.attr_value.value
        self._component_manager.update_device_assigned_resource(
            evt.device.dev_name(), new_value
        )

    def handle_dish_mode_event(self, event_flag: tango.EventData) -> None:
        """Method to handle and update the latest value of dishMode
        attribute.

        Args:
            event_flag (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self._logger.info("LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL subscribing")
        if event_flag.err:
            error = event_flag.errors[0]
            error_msg = f"{error.reason},{error.desc}"
            self._logger.error(error_msg)
            self._component_manager.update_event_failure()
            return
        new_value = event_flag.attr_value.value
        self._component_manager.update_device_dish_mode(
            event_flag.device.dev_name(), new_value
        )
        self._logger.info(f"DishMode value updated to {new_value}")

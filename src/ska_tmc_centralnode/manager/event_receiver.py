import tango
from ska_tmc_common.event_receiver import EventReceiver

from ska_tmc_centralnode.utils.constants import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
)


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
        except Exception as e:
            self._logger.error("Exception occured while creating proxy: %s", e)
        else:
            try:
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
                    proxy.subscribe_event(
                        "dishMode",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_dish_mode_event,
                        stateless=True,
                    )
                if "subarray_node" in dev_info.dev_name:
                    proxy.subscribe_event(
                        "longRunningCommandResult",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_lrcr_event,
                        stateless=True,
                    )
                    proxy.subscribe_event(
                        "isSubarrayAvailable",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_device_available_event,
                        stateless=True,
                    )

                if dev_info.dev_name in [
                    MID_CSP_MLN_DEVICE,
                    MID_SDP_MLN_DEVICE,
                    LOW_CSP_MLN_DEVICE,
                    LOW_SDP_MLN_DEVICE,
                ]:
                    proxy.subscribe_event(
                        "isSubsystemAvailable",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_device_available_event,
                        stateless=True,
                    )

            except Exception as e:
                self._logger.error(
                    "Event not working for device %s: %s", proxy.dev_name, e
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

    def handle_dish_mode_event(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of dishMode
        attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        if event_data.err:
            errors = event_data.errors
            for error in errors:
                error_msg = f"{error.reason},{error.desc}"
                self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_data.device.dev_name()
            )
            return
        new_value = event_data.attr_value.value
        self._component_manager.update_device_dish_mode(
            event_data.device.dev_name(), new_value
        )
        self._logger.info(f"DishMode value updated to {new_value}")

    def handle_lrcr_event(self, event_data: tango.EventData) -> None:
        """Method to handle and update the latest value of
        longRunningCommandResult attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        if event_data.err:
            errors = event_data.errors
            for error in errors:
                error_msg = f"{error.reason},{error.desc}"
                self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_data.device.dev_name()
            )
            return
        new_value = event_data.attr_value.value
        self._component_manager.update_long_running_command_result(
            event_data.device.dev_name(), new_value
        )

    def handle_device_available_event(
        self, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of isSubarrayAvailable
        attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        if event_data.err:
            errors = event_data.errors
            for error in errors:
                error_msg = f"{error.reason},{error.desc}"
                self._logger.error(error_msg)
                self._logger.error(str(event_data))
            self._component_manager.update_event_failure(
                event_data.device.dev_name()
            )
            return
        self._logger.info(str(event_data))
        new_value = event_data.attr_value.value
        self._component_manager.update_telescope_availability(
            event_data.device.dev_name(), new_value
        )

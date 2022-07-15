# import time

import tango
from ska_tmc_common.event_receiver import EventReceiver


class CentralNodeEventReceiver(EventReceiver):
    """
    The CentralNodeEventReceiver class has the responsibility to receive events
    from the sub devices managed by the Central node.

    # The ComponentManager uses the handle events methods
    # for the attribute of interest.
    # For each of them a callback is defined.

    TBD: what about scalability? what if we have 1000 devices?

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

    def subscribe_event(self, dev_info):
        try:
            proxy = self._dev_factory.get_device(dev_info.dev_name)
            proxy.subscribe_event(
                "assignedResources",
                tango.EventType.CHANGE_EVENT,
                self.handle_assigned_resource_event,
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
"""
This Module is used to Receive events from devices
"""
from concurrent import futures

import tango
from ska_tmc_common.event_receiver import EventReceiver


class SubarrayNodeEventReceiver(EventReceiver):
    """
    The SubarrayNodeEventReceiver class has the responsibility to receive events
    from the sub devices managed by the Subarray node.

    The ComponentManager uses the handle events methods
    for the attribute of interest.
    For each of them a callback is defined.

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
        self._component_manager = component_manager
        self._dish_pointing_state_event_ids = {}
        self._dish_health_state_event_ids = {}
        self._dish_state_event_ids = {}
        self._dish_leaf_health_state_event_ids = {}
        self._dish_leaf_state_event_ids = {}

    def subscribe_events(self, dev_info):
        """Method for subscribing events"""
        try:
            # import debugpy; debugpy.debug_this_thread()
            proxy = self._dev_factory.get_device(dev_info.dev_name)
            self._logger.debug(f"Proxy of device {dev_info.dev_name}: {proxy}")
            health_evt_id = proxy.subscribe_event(
                "healthState",
                tango.EventType.CHANGE_EVENT,
                self.handle_health_state_event,
                stateless=True,
            )
            state_evt_id = proxy.subscribe_event(
                "State",
                tango.EventType.CHANGE_EVENT,
                self.handle_state_event,
                stateless=True,
            )
            if "ska_mid/tm_leaf_node/d" in dev_info.dev_name:
                self._dish_leaf_state_event_ids[proxy] = state_evt_id
                self._dish_leaf_health_state_event_ids[proxy] = health_evt_id
            elif "dish/master" in dev_info.dev_name:
                self._dish_state_event_ids[proxy] = state_evt_id
                self._dish_health_state_event_ids[proxy] = health_evt_id
                pointing_evt_id = proxy.subscribe_event(
                    "pointingState",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_pointing_state_event,
                    stateless=True,
                )
                self._dish_pointing_state_event_ids[proxy] = pointing_evt_id

            elif (
                "subarray" in dev_info.dev_name
                and "leaf" not in dev_info.dev_name
            ):
                proxy.subscribe_event(
                    "ObsState",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_obs_state_event,
                    stateless=True,
                )
                if "tm_subarray_node" in dev_info.dev_name:
                    proxy.subscribe_event(
                        "isSubarrayAvailable",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_device_available_event,
                        stateless=True,
                    )

                if "sdp" in dev_info.dev_name:
                    proxy.subscribe_event(
                        "receiveAddresses",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_receive_addresses_event,
                        stateless=True,
                    )
                if "low-mccs" in dev_info.dev_name:
                    proxy.subscribe_event(
                        "assignedResources",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_assigned_resources_event,
                        stateless=True,
                    )

            elif "leaf" in dev_info.dev_name:
                proxy.subscribe_event(
                    "longRunningCommandResult",
                    tango.EventType.CHANGE_EVENT,
                    self.handle_lrcr_event,
                    stateless=True,
                )
                if "csp_master" or "sdp_master" in dev_info.dev_name:
                    proxy.subscribe_event(
                        "isSubsystemAvailable",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_device_available_event,
                        stateless=True,
                    )

        except Exception as e:
            self._logger.debug(
                "event not working for device %s/%s", proxy.dev_name, e
            )

    def unsubscribe_dish_events(self):
        """Method for unsubscribing dish events"""
        with futures.ThreadPoolExecutor(
            max_workers=self._max_workers
        ) as executor:
            if self._dish_pointing_state_event_ids:
                for proxy, evt_id in list(
                    self._dish_pointing_state_event_ids.items()
                ):
                    executor.submit(
                        self.unscubscribe_dish_pointing, proxy, evt_id
                    )
            if self._dish_health_state_event_ids:
                for proxy, evt_id in list(
                    self._dish_health_state_event_ids.items()
                ):
                    executor.submit(
                        self.unscubscribe_dish_health, proxy, evt_id
                    )
            if self._dish_state_event_ids:
                for proxy, evt_id in list(self._dish_state_event_ids.items()):
                    executor.submit(
                        self.unscubscribe_dish_state, proxy, evt_id
                    )

    def unscubscribe_dish_pointing(self, dish_proxy, evt_id):
        """Method for unsubscribing dish pointing"""
        try:
            dish_proxy.unsubscribe_event(evt_id)
            del self._dish_pointing_state_event_ids[dish_proxy]

        except Exception as e:
            self._logger.debug(
                "PointingState event unsubscription failed for device %s/%s",
                dish_proxy.dev_name,
                e,
            )

    def unscubscribe_dish_health(self, dish_proxy, evt_id):
        """Method for unsubscribing dish health"""
        try:
            dish_proxy.unsubscribe_event(evt_id)
            del self._dish_health_state_event_ids[dish_proxy]

        except Exception as e:
            self._logger.debug(
                "HealthState event unsubscription failed for device %s/%s",
                dish_proxy.dev_name,
                e,
            )

    def unscubscribe_dish_state(self, dish_proxy, evt_id):
        """Method for unsubscribing dish state"""
        try:
            dish_proxy.unsubscribe_event(evt_id)
            del self._dish_state_event_ids[dish_proxy]

        except Exception as e:
            self._logger.debug(
                "State event unsubscription failed for device %s/%s",
                dish_proxy.dev_name,
                e,
            )

    def unsubscribe_dish_leaf_events(self):
        """Method for unsubscribing dish leaf events."""
        # import debugpy; debugpy.debug_this_thread()
        with futures.ThreadPoolExecutor(
            max_workers=self._max_workers
        ) as executor:
            if self._dish_leaf_health_state_event_ids:
                for proxy, evt_id in list(
                    self._dish_leaf_health_state_event_ids.items()
                ):
                    executor.submit(
                        self.unscubscribe_dish_leaf_health, proxy, evt_id
                    )
            if self._dish_leaf_state_event_ids:
                for proxy, evt_id in list(
                    self._dish_leaf_state_event_ids.items()
                ):
                    executor.submit(
                        self.unscubscribe_dish_leaf_state, proxy, evt_id
                    )

    def unscubscribe_dish_leaf_health(self, dish_leaf_proxy, evt_id):
        """Method for unsubscribing dish leaf health"""
        try:
            dish_leaf_proxy.unsubscribe_event(evt_id)
            del self._dish_leaf_health_state_event_ids[dish_leaf_proxy]

        except Exception as e:
            self._logger.debug(
                "HealthState event unsubscription failed for device %s/%s",
                dish_leaf_proxy.dev_name,
                e,
            )

    def unscubscribe_dish_leaf_state(self, dish_leaf_proxy, evt_id):
        """Method for unsubscribing dish leaf health."""
        try:
            dish_leaf_proxy.unsubscribe_event(evt_id)
            del self._dish_leaf_state_event_ids[dish_leaf_proxy]

        except Exception as e:
            self._logger.debug(
                "State event unsubscription failed for device %s/%s",
                dish_leaf_proxy.dev_name,
                e,
            )

    def handle_pointing_state_event(self, evt):
        """Method for handling pointing state event."""
        # import debugpy; debugpy.debug_this_thread()
        evt_error_flag = self.check_event_error(evt)
        if evt_error_flag is True:
            return

        new_value = evt.attr_value.value
        self._component_manager.update_device_pointing_state(
            evt.device.dev_name(), new_value
        )

    def handle_receive_addresses_event(self, evt):
        """Method for handling and receiving addresses events."""
        # import debugpy; debugpy.debug_this_thread()
        evt_error_flag = self.check_event_error(evt)
        if evt_error_flag is True:
            return

        new_value = evt.attr_value.value
        self._component_manager.update_receive_addresses(
            evt.device.dev_name(), new_value
        )

    def handle_assigned_resources_event(self, evt):
        """Method for handling assigned resources events."""
        # import debugpy; debugpy.debug_this_thread()
        evt_error_flag = self.check_event_error(evt)
        if evt_error_flag is True:
            return

        new_value = evt.attr_value.value
        self._component_manager.update_assigned_resources(
            evt.device.dev_name(), new_value
        )

    def handle_lrcr_event(self, event):
        """Method for handling longRunningCommandResult events."""
        event_error_flag = self.check_event_error(event)
        if event_error_flag is True:
            return

        new_value = event.attr_value.value
        self._component_manager.update_long_running_command_result(
            event.device.dev_name(), new_value
        )

    def check_event_error(self, evt):
        """Method for checking event error."""
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            self._component_manager.update_event_failure(evt.device.dev_name())
            return True
        return False

    def handle_device_available_event(self, event):
        """Method for handling isSubarrayAvailable and isSubsystemAvailable events."""
        event_error_flag = self.check_event_error(event)
        if event_error_flag is True:
            return

        new_value = event.attr_value.value
        self._component_manager.update_telescope_availability(
            event.device.dev_name(), new_value
        )

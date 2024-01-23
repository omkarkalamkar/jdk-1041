import tango
from ska_tmc_common.event_receiver import EventReceiver

from ska_tmc_centralnode.model.input import InputParameterMid
from ska_tmc_centralnode.utils.constants import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MCCS_MLN_DEVICE,
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
            component_manager=component_manager,
            logger=logger,
            max_workers=max_workers,
            proxy_timeout=proxy_timeout,
            sleep_time=sleep_time,
        )
        self._component_manager = component_manager
        self.attribute_dictionary = {
            "state": self.handle_state_event,
            "healthState": self.handle_health_state_event,
        }

    def subscribe_events(self, dev_info, attribute_dictionary=None):
        super().subscribe_events(dev_info, self.attribute_dictionary)
        try:
            proxy = self._dev_factory.get_device(dev_info.dev_name)
        except Exception as e:
            self._logger.error(
                "Exception occurred while creating proxy: %s", e
            )
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
                    proxy.subscribe_event(
                        "obsState",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_obs_state_event,
                        stateless=True,
                    )
                if (
                    isinstance(
                        self._component_manager.input_parameter,
                        InputParameterMid,
                    )
                    and dev_info.dev_name
                    in self._component_manager.input_parameter.dish_dev_names
                ):
                    proxy.subscribe_event(
                        "dishMode",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_dish_mode_event,
                        stateless=True,
                    )
                if (
                    isinstance(
                        self._component_manager.input_parameter,
                        InputParameterMid,
                    )
                    and dev_info.dev_name
                    in self._component_manager.input_parameter.dish_leaf_node_dev_names
                ):
                    proxy.subscribe_event(
                        "kValueValidationResult",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_dln_kvalue_validation_result,
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
                        self.handle_subarray_availability_event,
                        stateless=True,
                    )

                if dev_info.dev_name in [
                    MID_CSP_MLN_DEVICE,
                    MID_SDP_MLN_DEVICE,
                    LOW_CSP_MLN_DEVICE,
                    LOW_SDP_MLN_DEVICE,
                    MCCS_MLN_DEVICE,
                ]:
                    proxy.subscribe_event(
                        "isSubsystemAvailable",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_masterln_availability_event,
                        stateless=True,
                    )

                    if dev_info.dev_name == MID_CSP_MLN_DEVICE:
                        proxy.subscribe_event(
                            "longRunningCommandResult",
                            tango.EventType.CHANGE_EVENT,
                            self.handle_load_dish_cfg_result_callback,
                            stateless=True,
                        )
                        proxy.subscribe_event(
                            "DishVccMapValidationResult",
                            tango.EventType.CHANGE_EVENT,
                            self.handle_dish_vcc_k_value_validation_event,
                            stateless=True,
                        )

                if dev_info.dev_name == MCCS_MLN_DEVICE:
                    proxy.subscribe_event(
                        "longRunningCommandResult",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_lrcr_event,
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
        self._logger.debug(
            f"In handle_lrcr_event event_data.attr_value.value is: {event_data.attr_value.value}"
        )
        new_value = event_data.attr_value.value
        self._component_manager.update_long_running_command_result(
            event_data.device.dev_name(), new_value
        )

    def handle_load_dish_cfg_result_callback(
        self, event_data: tango.EventData
    ) -> None:
        """This callback is called in following two scenario
        1. LongrunningResult returned from CspMasterLeafNode for LoadDishCfg command
        2. SetKValue command result returned from DishLeafNodes
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
        if getattr(event_data, "attr_value", False):
            self._logger.debug(
                f"In long running command result callback for csp master leaf node  "
                f"with event_data.attr_value.value is: {event_data.attr_value.value}"
            )
            new_value = event_data.attr_value.value
            self._component_manager.update_load_dish_cfg_results(
                event_data.device.dev_name(), new_value
            )
        # In case of Async callback get command result from argout
        elif getattr(event_data, "argout", False):
            self._logger.debug(
                f"Received Async callback event with event_data.argout is: {event_data.argout}"
            )
            new_value = event_data.argout
            self._component_manager.update_load_dish_cfg_results(
                event_data.device.dev_name(), new_value, is_async_result=True
            )

    def handle_dln_kvalue_validation_result(self, event_data: tango.EventData):
        """Method to handle kValueValidationResult from dish
        leaf node.
        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        if not event_data.errors:
            new_value = event_data.attr_value.value
            self._component_manager.dish_kvalue_validation_aggregator.aggregate(
                event_data.device.dev_name(), new_value
            )
        else:
            errors = event_data.errors
            for error in errors:
                error_msg = f"{error.reason},{error.desc}"
                self._logger.error(error_msg)
            self._component_manager.update_event_failure(
                event_data.device.dev_name()
            )

    def handle_dish_vcc_k_value_validation_event(
        self, event_data: tango.EventData
    ):
        """Handle DishVccValidationResult change event."""
        self._logger.info(
            "Event for DishVccValidationResult attribute: %s", event_data
        )
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
        if self._component_manager.enable_dish_vcc_init:
            new_value = event_data.attr_value.value
            self._component_manager.handle_dish_vcc_validation_result(
                event_data.device.dev_name(), new_value
            )

    def handle_masterln_availability_event(
        self, event_data: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of isSubsystemAvailable
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
        new_value = event_data.attr_value.value
        self._component_manager.update_telescope_availability(
            event_data.device.dev_name(), new_value
        )

    def handle_subarray_availability_event(
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
        new_value = event_data.attr_value.value
        self._component_manager.update_telescope_availability(
            event_data.device.dev_name(), new_value
        )

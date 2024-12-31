"""Event Receiver class for central node"""
from typing import Optional

import tango
from ska_tmc_common.device_info import DeviceInfo
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
        self.device_subscribed = {}
        self.dish_name = ""
        self.input_parameter = self._component_manager.input_parameter

    def submit_task(self, device_info: DeviceInfo) -> None:
        """Submits the task to the executor for the given device info object.

        :param executor: Threadpoolexecutor object

        :param device_info: DeviceInfo object for the device on which events
            are to be subscribed.
        :type device_info: DeviceInfo class object.

        :rtype: None
        """
        if device_info.dev_name not in self.device_subscribed:
            self._logger.info(
                "Subscribed events device_info.dev_name %s and %s",
                device_info.dev_name,
                self.device_subscribed,
            )

            self.subscribe_events(
                dev_info=device_info,
                attribute_dictionary=(self.attribute_dictionary),
            )

    def subscribe_events(
        self, dev_info: DeviceInfo, attribute_dictionary: Optional[dict] = None
    ) -> None:
        """Subscribe events for central node event receiver"""
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
                    in self.input_parameter.dish_leaf_node_dev_names
                ):
                    proxy.subscribe_event(
                        "dishMode",
                        tango.EventType.CHANGE_EVENT,
                        self.handle_dish_mode_event,
                        stateless=True,
                    )
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
            else:
                # Add device info in subscribed device
                self._logger.info("Subscribing device %s", dev_info.dev_name)
                self.device_subscribed[dev_info.dev_name] = True

    def handle_health_state_event(self, event: tango.EventData) -> None:
        """
        It handles the health state events of different devices
        """
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["healthState"].put(event)
        self._logger.info("exited callback")

    def handle_state_event(self, event: tango.EventData) -> None:
        """
        It handles the state events of different devices
        """
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["state"].put(event)
        self._logger.info("exited callback")

    def handle_assigned_resource_event(self, event: tango.EventData) -> None:
        """Handles assigned Resources event
        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["assignedResources"].put(event)
        self._logger.info("exited callback")

    def handle_dish_mode_event(self, event: tango.EventData) -> None:
        """Method to handle and update the latest value of dishMode
        attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["dishMode"].put(event)
        self._logger.info("exited callback")

    def handle_lrcr_event(self, event: tango.EventData) -> None:
        """Method to handle and update the latest value of
        longRunningCommandResult attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["longRunningCommandResult"].put(
            event
        )
        self._logger.info("exited callback")

    def handle_load_dish_cfg_result_callback(
        self, event: tango.EventData
    ) -> None:
        """This callback is called in following two scenario
        1. LongrunningResult returned from CspMasterLeafNode for
          LoadDishCfg command
        2. SetKValue command result returned from DishLeafNodes
        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self._logger.info("entered callback %s", event)
        if getattr(event, "attr_value", False):
            self._component_manager.event_queues["loadDishConfigResult"].put(
                event
            )
        # In case of Async callback get command result from argout
        elif getattr(event, "argout", False):
            self._component_manager.event_queues[
                "loadDishConfigResultAsync"
            ].put(event)
        self._logger.info("exited callback")

    def handle_dln_kvalue_validation_result(self, event: tango.EventData):
        """Method to handle kValueValidationResult from dish
        leaf node.
        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["kValueValidationResult"].put(
            event
        )
        self._logger.info("exited callback")

    def handle_dish_vcc_k_value_validation_event(self, event: tango.EventData):
        """Handle DishVccMapValidationResult change event."""
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["DishVccMapValidationResult"].put(
            event
        )
        self._logger.info("exited callback")

    def handle_masterln_availability_event(
        self, event: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of isSubsystemAvailable
        attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["isSubsystemAvailable"].put(event)
        self._logger.info("exited callback")

    def handle_subarray_availability_event(
        self, event: tango.EventData
    ) -> None:
        """Method to handle and update the latest value of isSubarrayAvailable
        attribute.

        Args:
            event_data (tango.EventType.CHANGE_EVENT): to flag the
            change in event.
        """
        self._logger.info("entered callback %s", event)
        self._component_manager.event_queues["isSubarrayAvailable"].put(event)
        self._logger.info("exited callback")

"""Module to manage all Mid telescope the change event callbacks.
"""
import json
import threading
import time
from logging import Logger
from typing import Callable

from ska_control_model import ResultCode
from ska_tmc_common import AdapterFactory
from ska_tmc_common.enum import DishMode
from tango import DevState

from ska_tmc_centralnode.manager.aggregators import (
    DishAttrValueAggregator,
    TelescopeAvailabilityAggregatorMid,
)
from ska_tmc_centralnode.model.enum import DishConfigStatus, ModesAvailability
from ska_tmc_centralnode.utils.constants import (
    DISH_VCC_VALIDATION_RESULT_STATUS,
    MID_CSP_MLN_DEVICE,
)

from ...model.component import TmcComponent
from ...model.input import InputParameterMid
from ..event_data_manager import EventDataManager
from .event_callback_manager import EventCallbackManager


class MidEventCallbackManager(EventCallbackManager):
    """Class to manage change event callbacks for Low telescope."""

    def __init__(
        self,
        logger: Logger,
        component: TmcComponent,
        command_completion_cond: threading.Condition,
        input_parameter: InputParameterMid,
        event_data_manager: EventDataManager,
        _aggregate_state: Callable,
        kvalue_validation_aggregator: DishAttrValueAggregator,
        gpm_aggregator: DishAttrValueAggregator,
        update_dish_vcc_flag: Callable,
        dish_vcc_command_invoke_cb: Callable,
        _telescope_availability_aggregator: TelescopeAvailabilityAggregatorMid,
        subarray_availability: dict,
        set_csp_mln_availability: Callable,
        set_sdp_mln_availability: Callable,
        gpm_invoke_command_callback: Callable,
        get_dish_vcc_command_status: Callable,
        dish_vcc_init_timeout: float,
        get_command_in_progress: Callable,
        set_command_in_progress: Callable,
        set_dish_vcc_command_status: Callable,
        set_dish_vcc_cmd_validation_status: Callable,
        global_pointing_model_status: dict,
        gpm_unknown_dishes: list,
        adapter_factory: AdapterFactory,
        check_if_csp_all_dish_ready: Callable,
    ):
        super().__init__(
            logger,
            component,
            command_completion_cond,
            input_parameter,
            event_data_manager,
            _aggregate_state,
        )
        self.input_parameter: InputParameterMid = input_parameter
        self.kvalue_validation_aggregator = kvalue_validation_aggregator
        self.update_dish_vcc_flag = update_dish_vcc_flag
        self.dish_vcc_command_invoke_cb = dish_vcc_command_invoke_cb
        self._telescope_availability_aggregator = (
            _telescope_availability_aggregator
        )
        self.subarray_availability = subarray_availability
        self.set_csp_mln_availability = set_csp_mln_availability
        self.set_sdp_mln_availability = set_sdp_mln_availability
        self.gpm_invoke_command_callback = gpm_invoke_command_callback
        self.get_dish_vcc_command_status = get_dish_vcc_command_status
        self.set_dish_vcc_command_status = set_dish_vcc_command_status
        self.dishln_gpm_lock = threading.RLock()
        self.dish_vcc_init_timeout = dish_vcc_init_timeout
        self.get_command_in_progress = get_command_in_progress
        self.set_command_in_progress = set_command_in_progress
        self.set_dish_vcc_cmd_validation_status = (
            set_dish_vcc_cmd_validation_status
        )
        self.global_pointing_model_status = global_pointing_model_status
        self.gpm_unknown_dishes = gpm_unknown_dishes
        self.adapter_factory = adapter_factory
        self.gpm_aggregator = gpm_aggregator
        self.check_if_csp_all_dish_ready = check_if_csp_all_dish_ready

    def _get_master_device_name(self, device_name: str):
        """Provides Master device name which is stored in device info.

        :param device_name: Device FQDN received in event.
        :type device_name: str
        """
        dev_name = super()._get_master_device_name(device_name)
        if not dev_name:
            if self.input_parameter.dish_leaf_node_prefix in device_name:
                dln_dev_names = self.input_parameter.dish_leaf_node_dev_names
                for dish in dln_dev_names:
                    if device_name in dish.lower():
                        dev_name = dish
            elif self.input_parameter.dish_master_identifier in device_name:
                # Update Dish Master device name with full FQDN in case of
                # real Dish
                dish_master_dev_names = self.input_parameter.dish_dev_names
                for dish in dish_master_dev_names:
                    if device_name in dish.lower():
                        dev_name = dish
        return dev_name

    def _is_dish_state_on(self) -> bool:
        """Checks if the dish state is ON.

        :return: Returns True if dish state is ON.
        :rtype: bool
        """
        is_dish_on: bool = False
        for dev_name in self.input_parameter.dish_dev_names:
            dish = self.component.get_device(dev_name)
            if (
                dish is not None
                and not dish.unresponsive
                and dish.state == DevState.ON
            ):
                is_dish_on = True
                break
        return is_dish_on

    def _get_csp_master_state(self) -> DevState:
        """Returns the CSP master state.

        :return: Returns CSP master state.
        :rtype: DevState
        """
        csp_state = DevState.UNKNOWN

        csp_master_device = self.component.get_device(
            self.input_parameter.csp_master_dev_name
        )
        if (
            csp_master_device is not None
            and not csp_master_device.unresponsive
        ):
            csp_state = csp_master_device.state
        return csp_state

    def _update_imaging(self) -> None:
        """
        Checks if CSP is ON and if atleast one Dish is ON. If both
        the conditions are true,
        it sets imaging to be available.
        """
        with self.lock:
            is_dish_state_on = self._is_dish_state_on()
            csp_state = self._get_csp_master_state()
            if csp_state == DevState.ON and is_dish_state_on:
                self.component.imaging = ModesAvailability.AVAILABLE
            else:
                self.component.imaging = ModesAvailability.NOT_AVAILABLE

    def _get_dish_leaf_node_name(self, device_name: str) -> str:
        """Provides Dish Leaf Node name as per device information

        :param device_name: Dish Leaf node received in event.
        :type device_name: str
        :return: Device name.
        :rtype: str
        """
        dish_leaf_node_dev_names = (
            self.input_parameter.dish_leaf_node_dev_names
        )
        for dish in dish_leaf_node_dev_names:
            if device_name in dish:
                device_name = dish
                break
        return device_name

    def update_device_dish_mode(
        self, dev_name: str, dish_mode: DishMode
    ) -> None:
        """
        Update the dish mode of the given dish leaf node
        and call the relative callbacks if available.

        Args:
            dev_name (str): Device name
            dishMode: Dish mode of the device

        """
        with self.rlock:
            self.logger.debug(
                f"Received dishMode event from {dev_name}: "
                + f"{DishMode(dish_mode).name}"
            )
            # Update Dish leaf node device name with full FQDN for real Dish
            dev_name = self._get_dish_leaf_node_name(dev_name)
            dev_info = self.component.get_device(dev_name)
            dev_info.dish_mode = dish_mode
            self.logger.debug(
                "Updated DishMode of %s: %s",
                dev_info.dev_name,
                DishMode(dev_info.dish_mode).name,
            )
            dev_info.last_event_arrived = time.time()

        self._aggregate_state()
        self._update_imaging()

    def update_k_value_validation(
        self, dev_name: str, kvalue: ResultCode
    ) -> None:
        """
        Updates the k value validation value and starts the aggregation.

        Args:
            dev_name (str): device name
            kvalue (ResultCode): k value validation result

        """
        self.kvalue_validation_aggregator.aggregate(dev_name, kvalue)

    def handle_dish_vcc_validation_result(
        self, dev_name: str, result: ResultCode
    ) -> None:
        """
        Handle Dish Vcc Validation Result
        Based on following table Result codes handled and attributes updated\n

        Result Code | Meaning\n
        UNKNOWN     | Dish Vcc Config not set on CSP\n
        OK          | Dish Vcc Config on CSP LN and CSP match\n
        FAILED      | Mismatch in dish vcc version on CSP LN and CSP Master\n
        NOT_ALLOWED | CSP master is not available\n\n

        Result Code | Action\n
        UNKNOWN     | Load Dish Config using LoadDishCfg command\n
        OK          | Dish Vcc already set so set is_dish_vcc_config_set
        to True\n
        FAILED      | Dish Vcc is mismatch so set set is_dish_vcc_config_set
        to False\n
        NOT_ALLOWED | Set is_dish_vcc_config_set to False

        Args:
            dev_name (str): Device name
            result (ResultCode): ResultCode

        """
        dish_vcc_validation_result = int(result)
        self.logger.debug(
            "Dish Vcc Validation Event called with %s and Result: %s",
            dev_name,
            ResultCode(dish_vcc_validation_result).name,
        )
        with self.dish_vcc_validation_attr_lock:
            if self.input_parameter.csp_mln_dev_name in dev_name:
                # Handle Csp Master Leaf Node event
                csp_validation_result = int(result)
                self.logger.debug(
                    "Csp Validation Result is %s",
                    ResultCode(csp_validation_result).name,
                )
                if (
                    csp_validation_result == ResultCode.UNKNOWN
                    and self.get_command_in_progress() != "LoadDishCfg"
                ):
                    # Unknown Result code sent when no dish vcc set
                    # so invoke LoadDishCfg

                    self.set_command_in_progress("LoadDishCfg")
                    if self.check_if_csp_all_dish_ready():
                        self.set_dish_vcc_command_status(DishConfigStatus.INIT)
                        self.dish_vcc_command_invoke_cb()
                    else:
                        self.logger.warning(
                            "Time Out while waiting for Dishes to be ready"
                        )
                        self.set_command_in_progress("")
                        # Initialization Failed so mark
                        # process status as failed
                        self.set_dish_vcc_command_status(
                            DishConfigStatus.FAILED
                        )
                elif (
                    csp_validation_result in DISH_VCC_VALIDATION_RESULT_STATUS
                ):
                    if csp_validation_result == ResultCode.OK:
                        # Update dish config status to completed only
                        # during central node initialization.
                        # This handle scenario when dish vcc already set
                        # and central node restart
                        if (
                            self.get_dish_vcc_command_status()
                            == DishConfigStatus.STAGING
                        ):
                            self.set_dish_vcc_command_status(
                                DishConfigStatus.COMPLETED
                            )
                        self.update_dish_vcc_flag(True)
                    else:
                        self.set_dish_vcc_command_status(
                            DishConfigStatus.FAILED
                        )
                        self.update_dish_vcc_flag(False)
                    validation_result = DISH_VCC_VALIDATION_RESULT_STATUS.get(
                        ResultCode(csp_validation_result)
                    )
                    self.set_dish_vcc_cmd_validation_status(
                        {MID_CSP_MLN_DEVICE: validation_result}
                    )

            with self.command_completion_cond:
                self.command_completion_cond.notify_all()

    def update_telescope_availability(
        self, device_name: str, event_value
    ) -> None:
        """
        Updates telescope availablity status

        Args:
            device_name (str): Device name
            event_value: Event value

        """
        with self.rlock:
            if device_name in self.input_parameter.subarray_dev_names:
                self.subarray_availability[device_name] = event_value
            elif self.input_parameter.csp_mln_dev_name == device_name:
                self.set_csp_mln_availability(event_value)
            elif self.input_parameter.sdp_mln_dev_name == device_name:
                self.set_sdp_mln_availability(event_value)
            self._telescope_availability_aggregator.aggregate()

    def update_device_state(self, device_name: str, state: DevState) -> None:
        """
        Update a monitored device state,
        aggregate the states available
        and call the relative callbacks if available

        Args:
            dev_name (str): name of the device
            state: state of the device

        """
        super().update_device_state(device_name, state)
        self._update_imaging()

    def handle_gpm_version_event(
        self, dev_name: str, gpm_version: str
    ) -> None:
        """
        Handle the GPM version
        Based on following table Result codes handled and attributes updated\n

        String       | Meaning\n
        UNKNOWN      | GPM version not set on Dish\n
        Version      | GPM is already invoked \n

        String      | Action\n
        UNKNOWN     | Apply GPM using SetGlobalPointingModel command\n
        Version     | Version is set, no need to invoke SetGlobalPointingModel
                      command

        Args:
            dev_name (str): Device name
            result (ResultCode): ResultCode

        """
        self.logger.debug(
            "GPM versions received %s from %s", gpm_version, dev_name
        )
        with self.dishln_gpm_lock:
            dish_id = dev_name.split("/")[-1]
            self.global_pointing_model_status = {
                dish_id: json.loads(gpm_version)
            }
            if self.check_if_csp_all_dish_ready():
                self.gpm_unknown_dishes = self.gpm_aggregator.aggregate_gpm()
                self.logger.debug(
                    "Command in progress %s and Dish-Vcc command status %s",
                    self.get_command_in_progress(),
                    self.get_dish_vcc_command_status(),
                )
                if (
                    self.gpm_unknown_dishes
                    and not self.get_command_in_progress()
                ):
                    if (
                        self.get_dish_vcc_command_status()
                        == DishConfigStatus.COMPLETED
                    ):
                        self.logger.info(
                            "Restart phase: Invoking Set GPM command on:  %s",
                            self.gpm_unknown_dishes,
                        )
                        self.gpm_invoke_command_callback()

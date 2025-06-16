"""
This module is inherited from CNComponentManager.

It is component Manager for Mid Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""

import json
import threading
import time
from logging import Logger
from queue import Queue
from typing import Callable, Tuple

from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode
from ska_tmc_common import AdapterType
from ska_tmc_common.enum import DishMode, LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from ska_tmc_centralnode.commands.load_dish_config_command import LoadDishCfg
from ska_tmc_centralnode.manager.aggregate_process import (
    HealthStateAggregationProcessor,
)
from ska_tmc_centralnode.manager.aggregators import (
    DishkValueValidationResultAggregator,
    LoadDishCfgCommandResultAggregator,
    TelescopeAvailabilityAggregatorMid,
    TelescopeStateAggregatorMid,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_MID,
    DISH_VCC_CONFIG_INTERFACE_VERSION,
    DISH_VCC_VALIDATION_RESULT_STATUS,
    MID_CSP_MLN_DEVICE,
)


# pylint:disable=too-many-instance-attributes
class CNComponentManagerMid(CNComponentManager):
    """Component manager class for central node mid"""

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        op_state_model,
        _input_parameter,
        logger: Logger,
        _dish_vcc_command_status_callback: callable,
        _update_device_callback: Callable,
        _update_telescope_state_callback: Callable,
        _update_telescope_health_state_callback: Callable,
        _update_tmc_op_state_callback: Callable,
        _update_imaging_callback: Callable,
        _telescope_availability_callback: Callable,
        _update_dishvccconfig_callback: Callable,
        _dishvccvalidation_callback: Callable,
        _component=None,
        _liveliness_probe=LivelinessProbeType.MULTI_DEVICE,
        _event_manager=True,
        proxy_timeout=500,
        event_subscription_check_period=1,
        liveliness_check_period=1,
        skuid_service="",
        command_timeout=30,
        dish_vcc_uri=None,
        dish_vcc_file_path=None,
        dish_vcc_init_timeout=120,
        dishKvalueAggregationAllowedPercent=100.0,
        invoke_load_dish_cfg_command_callback=None,
        enable_dish_vcc_init=True,
        k_value_valid_range_upper_limit=1177,
        k_value_valid_range_lower_limit=1,
        subarray_trl_prefix: str = "mid-tmc/subarray",
        *args,
        **kwargs,
    ) -> None:
        """
        Initialise a new ComponentManager instance for mid.

        Args:
            op_state_model: the op state model used by this
                component manager
            logger:
                a logger for this component manager
            _component: allows setting of the component to be
                managed; for testing purposes only
            _input_parameter :
                specify input parameter for mid.
            _liveliness_probe:
                allows to enable/disable LivelinessProbe usage
            _event_manager : allows to enable/disable
                EventManager usage
            max_workers: Optional. Maximum worker
                threads for monitoring purpose.
            proxy_timeout: Optional. Time period to wait for
                event and responses.
            event_subscription_check_period (int): Time in seconds
                for sleep intervals in the event subsription thread.
            liveliness_check_period (int): Period for the
                liveliness probe to monitor each device in a loop
            timeout : Optional. Time period to wait for
                intialization of adapter.
            skuid_service:
                SKUId service
            command_timeout:
                Command timeout
            dish_vcc_uri:
                Dish vcc uri
            dish_vcc_file_path:
                dish vcc file path
            dish_vcc_init_timeout:
                dish vcc default timeout
            dishKvalueAggregationAllowedPercent:
                dish Kvalue aggregation default
            invoke_load_dish_cfg_command_callback:
                callback for invoke load dish
            enable_dish_vcc_init:
                enable dish vcc
            k_value_valid_range_upper_limit:
                k value upper limit
            k_value_valid_range_lower_limit:
                k value lower limit.

        """
        super().__init__(
            op_state_model,
            _input_parameter,
            logger,
            _update_device_callback,
            _update_telescope_state_callback,
            _update_telescope_health_state_callback,
            _update_tmc_op_state_callback,
            _update_imaging_callback,
            _telescope_availability_callback,
            _component,
            _liveliness_probe,
            _event_manager,
            proxy_timeout,
            event_subscription_check_period,
            liveliness_check_period,
            skuid_service,
            command_timeout,
            subarray_trl_prefix,
            *args,
            **kwargs,
        )

        self.subarray_availability = {
            subarray: False
            for subarray in self.input_parameter.subarray_dev_names
        }
        self.csp_mln_availability = False
        self.sdp_mln_availability = False
        telescope_availability = self.get_telescope_availability()
        telescope_availability["tmc_subarrays"] = self.subarray_availability
        self.set_telescope_availability = telescope_availability

        self._telescope_availability_aggregator = (
            TelescopeAvailabilityAggregatorMid(self, self.logger)
        )

        self._is_dish_vcc_config_set = False
        self.dish_vcc_uri = dish_vcc_uri
        self.dish_vcc_file_path = dish_vcc_file_path
        self.dish_vcc_init_timeout = dish_vcc_init_timeout
        self.invoke_load_dish_cfg_command_callback = (
            invoke_load_dish_cfg_command_callback
        )
        self.dishKvalueAggregationAllowedPercent = (
            dishKvalueAggregationAllowedPercent
        )
        self.dish_kvalue_validation_aggregator = (
            DishkValueValidationResultAggregator(self, self.logger)
        )
        self.dev_names_for_load_dish_cfg = []
        self.load_dish_cfg_aggregated_result = None
        self.load_dish_cfg_command_id = None
        self._dish_vcc_validation_status = "{}"
        self.dish_vcc_validation_attr_lock = threading.Lock()
        self.enable_dish_vcc_init = enable_dish_vcc_init
        self.command_result = None
        self.k_value_valid_range_upper_limit = k_value_valid_range_upper_limit
        self.k_value_valid_range_lower_limit = k_value_valid_range_lower_limit
        self.update_dishvccconfig_callback = _update_dishvccconfig_callback
        self.dishvccvalidation_callback = _dishvccvalidation_callback
        self.dish_vcc_data_download_error = False
        self._dish_vcc_command_status = DishConfigStatus.STAGING
        self.dish_vcc_command_status_callback = (
            _dish_vcc_command_status_callback
        )
        self.event_queue.update(
            {
                "longRunningCommandResult": Queue(),
                "dishMode": Queue(),
                "kValueValidationResult": Queue(),
                "DishVccMapValidationResult": Queue(),
                "isSubsystemAvailable": Queue(),
                "isSubarrayAvailable": Queue(),
                "state": Queue(),
                "loadDishConfigResult": Queue(),
                "loadDishConfigResultAsync": Queue(),
            }
        )
        handle_dish_vcc = self.handle_dish_vcc_validation_result
        self.event_processing_methods.update(
            {
                "longRunningCommandResult": (
                    self.update_long_running_command_result
                ),
                "dishMode": self.update_device_dish_mode,
                "kValueValidationResult": self.update_k_value_validation,
                "DishVccMapValidationResult": handle_dish_vcc,
                "isSubsystemAvailable": self.update_telescope_availability,
                "isSubarrayAvailable": self.update_telescope_availability,
                "state": self.update_device_state,
                "loadDishConfigResult": self.update_load_dish_cfg_results,
                "loadDishConfigResultAsync": (
                    self.update_load_dish_cfg_results_async
                ),
            }
        )
        self._start_event_processing_threads()
        # start the aggregation process
        self.aggregation_process = HealthStateAggregationProcessor(
            self.event_data_queue,
            self.aggregated_health_state,
            self.aggregate_value_update_event,
            telescope="mid",
        )
        self.aggregation_process.start_aggregation_process()

    def check_if_dishes_are_responsive(self) -> bool:
        """
        Checks whether dishes are responsive

        Returns:
            True, if dishes are responsive,
            False otherwise

        """
        self.logger.info("Checking if dishes are responsive")
        return self._check_if_device_is_responsive(
            self.input_parameter.dish_leaf_node_dev_names
        )

    def get_load_disg_cfg_resultcode(self) -> ResultCode:
        """
        Return Aggregated command result for Load Dish Cfg command

        Returns:
            Aggregated command result for Load Dish Cfg command

        """
        return self.load_dish_cfg_aggregated_result

    @property
    def dish_vcc_command_status(self):
        """Return dish vcc command status"""
        return self._dish_vcc_command_status

    @dish_vcc_command_status.setter
    def dish_vcc_command_status(self, value: DishConfigStatus):
        """Set dish vcc command status and invoke callback"""
        self.logger.debug("Setting dish config status %s", str(value))
        self._dish_vcc_command_status = value
        self.dish_vcc_command_status_callback(value)

    @property
    def is_dish_vcc_config_set(self):
        """Getter method for is_dish_vcc_config_set"""
        return self._is_dish_vcc_config_set

    @is_dish_vcc_config_set.setter
    def is_dish_vcc_config_set(self, value):
        """Setter method for is_dish_vcc_config_set"""
        self._is_dish_vcc_config_set = value

    @property
    def dish_vcc_validation_status(self) -> dict:
        """
        Getter method for dish vcc validation status

        Returns:
            dish: dish vcc validation status

        """
        return self._dish_vcc_validation_status

    @dish_vcc_validation_status.setter
    def dish_vcc_validation_status(self, validation_status: dict):
        """
        This method does the aggregation from Dish and CSPMLN
        and sets the updated validation result.

        Ex1:
            .. code-block:: json

                current_dish_vcc_validation_status = '{
                    "ska001": "k-value not set",
                    "ska036": "k-value not set",
                    "ska063": "k-value not set",
                    "ska100": "k-value not set",
                    "mid-tmc/leaf-node-csp/0":
                    "TMC and CSP Master Dish Vcc Version is Same",
                }'
                validation_status = {
                    "ska001": "k-value identical",
                    "ska036": "k-value identical",
                    "ska063": "k-value not set",
                    "ska100": "k-value not set",
                }

        if validation_status received and current validation status is
        as above then this method will aggregate like below:

        .. code-block:: json
            self._dish_vcc_validation_status = '{
                "ska001": "k-value identical",
                "ska036": "k-value identical",
                "ska063": "k-value not set",
                "ska100": "k-value not set",
                "mid-tmc/leaf-node-csp/0":
                "TMC and CSP Master Dish Vcc Version is Same",
            }'

        or Ex2:
        if validation_status = {"dish":"ALL DISH OK"}
        then:

        .. code-block:: json
            self._dish_vcc_validation_status = '{
                "dish":"ALL DISH OK",
                "TMC and CSP Master Dish Vcc Version is Same",
            }'

        """
        csp_validation_status = ""
        # Copying here as dictionary is getting passed by reference.
        updated_validation_status = validation_status.copy()
        current_dish_vcc_validation_status = json.loads(
            self._dish_vcc_validation_status
        )
        # Extract existing CSPMLN result
        if MID_CSP_MLN_DEVICE in current_dish_vcc_validation_status:
            csp_validation_status = {
                MID_CSP_MLN_DEVICE: current_dish_vcc_validation_status[
                    MID_CSP_MLN_DEVICE
                ]
            }

        # If all Dish are set, remove all other instances
        if "dish" in updated_validation_status:
            # Overwrite the results
            current_dish_vcc_validation_status = updated_validation_status
            self.is_dish_vcc_config_set = True
            if csp_validation_status:
                if (
                    csp_validation_status[MID_CSP_MLN_DEVICE]
                    != DISH_VCC_VALIDATION_RESULT_STATUS[ResultCode.OK]
                ):
                    self.is_dish_vcc_config_set = False

                current_dish_vcc_validation_status.update(
                    csp_validation_status
                )
        elif CENTRALNODE_MID in updated_validation_status:
            current_dish_vcc_validation_status.update(
                updated_validation_status
            )
        else:
            # If the event from dish only
            if MID_CSP_MLN_DEVICE not in updated_validation_status:
                # Remove dish value from existing value
                current_dish_vcc_validation_status.pop("dish", None)
                # Overwrite the results
                current_dish_vcc_validation_status = updated_validation_status
                if csp_validation_status:
                    current_dish_vcc_validation_status.update(
                        csp_validation_status
                    )
            else:
                # If the event from CSPMLN only
                current_dish_vcc_validation_status.update(
                    updated_validation_status
                )
        self._dish_vcc_validation_status = json.dumps(
            {
                key: value
                for key, value in current_dish_vcc_validation_status.items()
                if value != "k-value identical"
            }
        )
        self.dishvccvalidation_callback(self._dish_vcc_validation_status)
        # empty the dictionaries
        current_dish_vcc_validation_status = {}
        updated_validation_status = {}

    def is_csp_dish_ready(self) -> bool:
        """
        his method wait for csp master leaf node and
        dish leaf nodes to become ready to accept request

        Returns:
            True, if csp master leaf node and
            dish leaf nodes are ready, False otherwise

        """
        count = 0
        devices_to_check_list = [self.input_parameter.csp_mln_dev_name]
        devices_to_check_list.extend(
            self.input_parameter.dish_leaf_node_dev_names
        )

        dev_state_list = [
            self.get_device(device).state for device in devices_to_check_list
        ]
        while True:
            if set(dev_state_list) == set([DevState.ON]):
                return True
            time.sleep(1)
            dev_state_list = [
                self.get_device(device).state
                for device in devices_to_check_list
            ]
            self.logger.debug("Current device states: %s", str(dev_state_list))
            count += 1
            if count == self.dish_vcc_init_timeout:
                break
        return False

    def update_long_running_command_result(
        self, dev_name: str, value: tuple
    ) -> None:
        """
        Updates the LRCR callback with received event.

        Value contains (unique_id, ResultCode) or (unique_id,exception_msg)
        or (unique_id,TaskStatus)
        Whenever there is exception occured , (unique_id,exception_msg)
        event is first raised
        and catched in ValueError.The exception_msg and command_id is then
        passed to long_running_result_callback.
        Command_mapping contains {centralnode_command_id:unique_id} ,
        all events are verified with respect to this mapping.
        If there is no command_mapping present the event
        might be of old command.

        Args:
            dev_name (str): name of the device who's event has been
                captured in this method
            value: longRunningCommandResult attribute event.

        """
        self.logger.debug(
            "Command ID: %s | longRunningCommandResult event for "
            + "device %s. Event value: %s",
            self.command_id,
            dev_name,
            str(value),
        )
        unique_id, result_code_or_exception_or_task_status = value
        if (
            not unique_id.endswith(self.supported_commands)
            or not result_code_or_exception_or_task_status
            or unique_id not in self.command_mapping.values()
        ):
            return
        try:
            result_code, message = json.loads(
                result_code_or_exception_or_task_status
            )
            match int(result_code):
                case ResultCode.OK:
                    self.command_result = ResultCode.OK
                    self.logger.debug(
                        "Command ID: %s | Command with Unique ID %s on "
                        + "%s succeeded.",
                        self.command_id,
                        str(unique_id),
                        dev_name,
                    )
                case (
                    ResultCode.FAILED
                    | ResultCode.REJECTED
                    | ResultCode.NOT_ALLOWED
                    | ResultCode.ABORTED
                ):
                    self.logger.debug(
                        "Command ID: %s | Updating LRCRCallback with "
                        + "ResultCode: %s and Message: %s "
                        + "for command %s on  %s.",
                        self.command_id,
                        ResultCode(result_code),
                        message,
                        str(unique_id),
                        dev_name,
                    )

                    exp_string = (
                        f"Exception occurred on device: {unique_id}: "
                        f"{dev_name}: {message}"
                    )
                    command_id = self.get_command_id(unique_id)
                    self.long_running_result_callback(
                        command_id,
                        ResultCode.FAILED,
                        exception_msg=exp_string,
                    )
                    self.observable.notify_observers(command_exception=True)
        except Exception as exception:
            self.logger.exception(
                "Command ID: %s | Exception occurred while processing "
                + "long running command result on %s: %s",
                self.command_id,
                dev_name,
                exception,
            )

    def get_command_id(self, unique_id: int) -> str:
        """
        This Method is used to get command
        it from the command mapping dictionary

        Args:
            unique_id (int): unique id of the command

        Returns:
            str: returns the command id with reference to unique id.

        """
        index_of_unique_id = list(self.command_mapping.values()).index(
            unique_id
        )  # get index location of unique_id received in event
        command_id = list(self.command_mapping.keys())[
            index_of_unique_id
        ]  # command id mapped to unique id
        return command_id

    def update_device_state(self, device_name: str, state: DevState) -> None:
        """
        Update a monitored device state,
        aggregate the states available
        and call the relative callbacks if available

        Args:
            dev_name (str): name of the device
            state: state of the device

        """
        with self.rlock:
            self.logger.debug(f"State event for {device_name}: {state}")

            if "sdp" in device_name:
                # Update SDP Master device name with full FQDN for real SDP
                sdp_master_dev_name = self.get_sdp_master_dev_name()
                if device_name in sdp_master_dev_name:
                    device_name = sdp_master_dev_name
            if "csp" in device_name:
                # Update CSP Master device name with full FQDN for real CSP
                csp_master_dev_name = self.get_csp_master_dev_name()
                if device_name in csp_master_dev_name:
                    device_name = csp_master_dev_name
            if self.input_parameter.dish_master_identifier in device_name:
                # Update Dish Master device name with full FQDN in case of
                # real Dish
                dish_master_dev_names = self.get_dish_device_names()
                for dish in dish_master_dev_names:
                    if device_name in dish.lower():
                        device_name = dish

            devInfo = self.component.get_device(device_name)
            if devInfo is not None:
                devInfo.state = state
                self.logger.debug(
                    f"Updated Device State of {devInfo.dev_name}: "
                    f"{devInfo.state}"
                )
                devInfo.last_event_arrived = time.time()
                devInfo.update_unresponsive(False)
                self.component._invoke_device_callback(devInfo)

        self._aggregate_state()
        self._update_imaging()

    def get_dish_leaf_node_device_names(self) -> tuple:
        """
        Return Dish leaf node device names

        Returns:
            A tuple of dish leaf node devices names

        """
        return self.input_parameter.dish_leaf_node_dev_names

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
            dish_leaf_node_dev_names = self.get_dish_leaf_node_device_names()
            for dish in dish_leaf_node_dev_names:
                if dev_name in dish:
                    dev_name = dish

            dev_info = self.component.get_device(dev_name)
            dev_info.dish_mode = dish_mode
            self.logger.debug(
                "Updated DishMode of %s: %s",
                dev_info.dev_name,
                DishMode(dev_info.dish_mode).name,
            )
            dev_info.last_event_arrived = time.time()
            dev_info.update_unresponsive(False)

        self._aggregate_state()
        self._update_imaging()

    def add_dishes(self, dln_prefix: str, num_dishes: int) -> list:
        """
        Add dishes to the liveliness probe function

        Args:
            dln_prefix (str): prefix of the dish
            num_dishes (int): number of dishes

        Returns:
            List of dishes

        """
        result = []
        for dish in range(1, (num_dishes + 1)):
            self.add_device(f"{dln_prefix}{dish:03d}")
            result.append(f"{dln_prefix}{dish:03d}")
        return result

    def _aggregate_telescope_state(self) -> None:
        """
        Aggregates telescope state
        """
        if self._telescope_state_aggregator is None:
            self._telescope_state_aggregator = TelescopeStateAggregatorMid(
                self, self.logger
            )

        with self.rlock:
            new_state = self._telescope_state_aggregator.aggregate()
            self.component.telescope_state = new_state

    def stop_aggregation_process(self) -> None:
        """Stop aggregation process"""
        self.aggregation_process.stop_aggregation_process()

    def is_command_allowed(self, command_name=None) -> bool:
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the
        component needed for the operation are not unresponsive

        Args:
            command_name (str): name of the command

        Returns:
            True if this command is allowed

        """
        if self.enable_dish_vcc_init:
            if not self.is_dish_vcc_config_set and command_name not in [
                "TelescopeOff",
                "TelescopeStandby",
                "LoadDishCfg",
            ]:
                raise CommandNotAllowed(
                    "Dish Vcc Config not Set. Please set using LoadDishCfg"
                    " command. "
                    "Current Telescope State is :"
                    + f"{str(self.op_state_model.op_state)}",
                )
        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            self.logger.info(
                f"{command_name} command is not supported "
                + f"in {self.op_state_model.op_state} for CentralNode"
            )
            raise CommandNotAllowed(
                "Command is not allowed in current state :"
                + f"{str(self.op_state_model.op_state)}",
            )
        return True

    def check_device_responsiveness_command(self, command_name: str) -> None:
        """
        This method overrides the method from super class
        to add responsive checks for the devices

        Args:
            command_name (str): Command name for the check

        """
        if command_name in self.supported_commands_for_responsive_check:
            self.logger.debug(f"Checking mid devices for {command_name}")
            self.check_if_subarrays_are_responsive()
            self.check_if_dishes_are_responsive()

    def update_k_value_validation(
        self, dev_name: str, kvalue: ResultCode
    ) -> None:
        """
        Updates the k value validation value and starts the aggregation.

        Args:
            dev_name (str): device name
            kvalue (ResultCode): k value validation result

        """
        self.dish_kvalue_validation_aggregator.aggregate(dev_name, kvalue)

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
                self.csp_mln_availability = event_value
            elif self.input_parameter.sdp_mln_dev_name == device_name:
                self.sdp_mln_availability = event_value
            self._telescope_availability_aggregator.aggregate()

    def update_dish_vcc_flag(self, value: bool) -> None:
        """
        Update dish vcc flag and call telescope state
        aggregator

        Args:
            value (bool): Value of the dish vcc config flag

        """
        self.logger.debug("Updating dish vcc config set flag to %s", value)
        self.is_dish_vcc_config_set = value
        self.update_dishvccconfig_callback(self.is_dish_vcc_config_set)
        self._aggregate_telescope_state()

    def get_default_dish_vcc_config_params(self) -> dict:
        """
        Return default dish vcc config json

        Returns:
            Default dish vcc config json

        """
        return {
            "interface": DISH_VCC_CONFIG_INTERFACE_VERSION,
            "tm_data_sources": [self.dish_vcc_uri],
            "tm_data_filepath": self.dish_vcc_file_path,
        }

    def check_if_csp_all_dish_ready(self) -> bool:
        """
        Check and validate all dish and csp master is ready

        Returns:
            `True`, if all dish and csp master is ready,
            `False`, otherwise.

        """
        count = 0
        num_of_dish_values = {}
        # This loop keep checking for kvalueValidationResult values
        # from all dishes which confirm that event is received from
        # all dishes
        while count <= self.dish_vcc_init_timeout:
            try:
                for dish_name in self.input_parameter.dish_leaf_node_dev_names:
                    if dish_name not in num_of_dish_values:
                        adapter = self.adapter_factory.get_or_create_adapter(
                            dish_name, adapter_type=AdapterType.DISH
                        )
                        k_val_result = adapter._proxy.kValueValidationResult
                        if k_val_result != "1":
                            num_of_dish_values[dish_name] = k_val_result
                if len(num_of_dish_values) == len(
                    self.input_parameter.dish_leaf_node_dev_names
                ):
                    self.logger.info("All dishes are available and ready.")
                return True
            except Exception as e:
                self.logger.exception("Error %s", str(e))
            count += 1
            time.sleep(1)
        return False

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
            ObsState(dish_vcc_validation_result).name,
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
                    and self.command_in_progress != "LoadDishCfg"
                ):
                    # Unknown Result code sent when no dish vcc set
                    # so invoke LoadDishCfg

                    self.command_in_progress = "LoadDishCfg"
                    if self.check_if_csp_all_dish_ready():
                        self.dish_vcc_command_status = DishConfigStatus.INIT
                        self.invoke_load_dish_cfg_command_callback()
                    else:
                        self.logger.debug(
                            "Time Out while waiting for Dishes to be ready"
                        )
                        self.command_in_progress = ""
                        # Initialization Failed so mark
                        # process status as failed
                        self.dish_vcc_command_status = DishConfigStatus.FAILED
                elif (
                    csp_validation_result in DISH_VCC_VALIDATION_RESULT_STATUS
                ):
                    if csp_validation_result == ResultCode.OK:
                        # Update dish config status to completed only
                        # during central node initialization.
                        # This handle scenario when dish vcc already set
                        # and central node restart
                        if (
                            self.dish_vcc_command_status
                            == DishConfigStatus.STAGING
                        ):
                            self.dish_vcc_command_status = (
                                DishConfigStatus.COMPLETED
                            )
                        self.update_dish_vcc_flag(True)
                    else:
                        self.dish_vcc_command_status = DishConfigStatus.FAILED
                        self.update_dish_vcc_flag(False)
                    self.dish_vcc_validation_status = {
                        MID_CSP_MLN_DEVICE: DISH_VCC_VALIDATION_RESULT_STATUS[
                            csp_validation_result
                        ]
                    }

    def load_dish_cfg(
        self, argin: str, task_callback: Callable = None
    ) -> Tuple[ResultCode, str]:
        """
        Load Dish Cfg command for Dish-VCC map.

        Args:
            argin (str): Dish Id Vcc map initial params

        Returns:
            a result code and message

        """
        loadishcfg_command = LoadDishCfg(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )
        self.logger.debug(
            "Command Status: %s ",
            str(DishConfigStatus(self.dish_vcc_command_status).name),
        )
        if self.dish_vcc_command_status in (
            DishConfigStatus.STAGING,
            DishConfigStatus.IN_PROGRESS,
        ):
            message = (
                "Dish Vcc Configuration is in Progress. "
                "Dish Vcc command status: %s ",
                str(DishConfigStatus(self.dish_vcc_command_status).name),
            )
            return loadishcfg_command.reject_command(message)

        try:
            dishid_vcc_map_params = json.loads(argin)
            self.logger.debug("JSON argin is in correct format.")
        except json.JSONDecodeError as e:
            self.dish_vcc_validation_status = {
                CENTRALNODE_MID: "JsonDecodeError"
            }
            return loadishcfg_command.reject_command(
                f"The JSON string is malformed. Error: {str(e)}",
            )
        (
            dishid_vcc_map_json,
            error_message,
        ) = loadishcfg_command.get_dishid_vcc_map_json(dishid_vcc_map_params)
        if error_message:
            self.dish_vcc_validation_status = {CENTRALNODE_MID: error_message}
            self.dish_vcc_data_download_error = True
            task_status, response = self.submit_task(
                loadishcfg_command.load_dish_cfg,
                args=[argin, self.logger],
                task_callback=task_callback,
            )
            return task_status, response
        self.logger.debug(
            "DishId Vcc Map Json: %s",
            json.dumps(dishid_vcc_map_json, indent=4),
        )
        (
            is_valid_dish_cfg,
            message,
        ) = loadishcfg_command.load_dish_config_json_validator(
            dishid_vcc_map_json
        )

        if not is_valid_dish_cfg:
            if message:
                self.dish_vcc_validation_status = {CENTRALNODE_MID: message}
            return loadishcfg_command.reject_command(
                message,
            )

        task_status, response = self.submit_task(
            loadishcfg_command.load_dish_cfg,
            args=[argin, self.logger],
            task_callback=task_callback,
        )
        return task_status, response

    def update_load_dish_cfg_results_async(
        self, dev_name: str, value: tuple
    ) -> None:
        """
        This method is used to update the result returned
        from Csp Master Leaf Node
        and returned from Dish Leaf Nodes for SetKValue command.

        Args:
            dev_name (str): name of the device who's event
                has been captured in this method
            value: longRunningCommandResult attribute event.

        """
        self.update_load_dish_cfg_results(
            dev_name, value, is_async_result=True
        )

    def update_load_dish_cfg_results(
        self, dev_name: str, value: tuple, is_async_result: bool = False
    ) -> None:
        """
        This method is used to update the result returned
        from Csp Master Leaf Node
        and returned from Dish Leaf Nodes for SetKValue command.
        Update result_codes_mapping with dev name as a key and
        command result as a value
        If all events are received from all device then aggregate
        the result
        Value contains (unique_id, ResultCode) or (unique_id,exception_msg)
        or (unique_id,TaskStatus)

        Args:
            dev_name (str): name of the device who's event has been
                captured in this method
            value (tuple): longRunningCommandResult attribute event.
            is_async_result (bool): Whether this callback is called
                from Async command result call or
                longRunningCommandResult attribute callback

        Examples of value:
            .. code-block:: python

                Async callback value: [array([0], dtype=int32), ['']]

                LongRunningCommandResultCallBack value:
                ('1698838234.9087641-LoadDishCfg',
                'Exception occurred, command failed.')

        """
        self.logger.debug(
            "longRunningCommandResult event for device: %s, with value: %s",
            dev_name,
            str(value),
        )
        with self.rlock:
            result_code_or_exception = []
            if is_async_result:
                # Set result code and message
                self.logger.debug(
                    "Event from asynchronous command result callback %s",
                    str(value),
                )
                result_code_or_exception = [value[0][0], value[1][0]]

            else:
                self.logger.debug(
                    "Event from long command result callback %s", str(value)
                )
                unique_id, resultcode_message = value
                if unique_id.endswith("LoadDishCfg"):
                    result_code_or_exception = json.loads(resultcode_message)
            if result_code_or_exception and self.dev_names_for_load_dish_cfg:
                self.result_codes_mapping[dev_name] = result_code_or_exception
                self.logger.debug(
                    "Dev names for load_dish_cfg values %s "
                    + "and result_codes_mapping are %s",
                    str(self.dev_names_for_load_dish_cfg),
                    str(self.result_codes_mapping),
                )

            # When all events received from dishes and Csp master leaf node
            # then aggregate the result
            if len(self.dev_names_for_load_dish_cfg) == len(
                self.result_codes_mapping
            ):
                # Aggregate the result
                self.logger.debug(
                    "All Events received for load dish cfg Aggregating results"
                )
                self.aggregate_load_dish_cfg_results()

    def aggregate_load_dish_cfg_results(self) -> None:
        """
        This method aggregate load dish cfg command result based on
        generated data
        """
        load_dish_cfg_aggregator = LoadDishCfgCommandResultAggregator(
            self, self.logger
        )
        (
            load_dish_cfg_aggregated_result,
            message,
        ) = load_dish_cfg_aggregator.aggregate()
        self.load_dish_cfg_aggregated_result = load_dish_cfg_aggregated_result
        if (
            self.load_dish_cfg_aggregated_result == ResultCode.FAILED
            and self.load_dish_cfg_command_id
        ):
            exception_message = f"Exception occurred on device: {message}"
            self.long_running_result_callback(
                self.load_dish_cfg_command_id,
                ResultCode.FAILED,
                exception_msg=exception_message,
            )
            self.observable.notify_observers(command_exception=True)

    def reset_load_dish_cfg_data(self) -> None:
        """Reset all data which is set for aggregating LoadDisgCfg command"""
        self.logger.info("Resetting LoadDishCfg aggregated data")
        self.load_dish_cfg_aggregated_result = ""
        self.dev_names_for_load_dish_cfg = []
        self.result_codes_mapping = {}
        self.load_dish_cfg_command_id = None
        self.dish_vcc_data_download_error = False
        self.dish_vcc_command_status = DishConfigStatus.COMPLETED

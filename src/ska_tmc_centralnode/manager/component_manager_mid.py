"""
This module is inherited from CNComponentManager.

It is component Manager for Mid Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import json
import threading
import time
from queue import Queue
from typing import Callable

from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common import AdapterType
from ska_tmc_common.enum import DishMode, LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from ska_tmc_centralnode.commands.load_dish_config_command import LoadDishCfg
from ska_tmc_centralnode.manager.aggregators import (
    DishkValueValidationResultAggregator,
    HealthStateAggregatorMid,
    LoadDishCfgCommandResultAggregator,
    TelescopeAvailabilityAggregatorMid,
    TelescopeStateAggregatorMid,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
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
        logger=None,
        _component=None,
        _liveliness_probe=LivelinessProbeType.MULTI_DEVICE,
        _event_receiver=True,
        _update_device_callback=None,
        _update_telescope_state_callback=None,
        _update_telescope_health_state_callback=None,
        _update_tmc_op_state_callback=None,
        _update_imaging_callback=None,
        _telescope_availability_callback=None,
        _update_dishvccconfig_callback=None,
        _dishvccvalidation_callback=None,
        communication_state_callback=None,
        component_state_callback=None,
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
        *args,
        **kwargs,
    ):
        """
        Initialise a new ComponentManager instance for mid.

        :param op_state_model: the op state model used by this component
            manager
        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        :param _input_parameter : specify input parameter for mid.
        :param _liveliness_probe:allows to enable/disable LivelinessProbe usage
        :param _event_receiver : allows to enable/disable EventReceiver usage
        :param max_workers: Optional. Maximum worker threads for
            monitoring purpose.
        :param proxy_timeout: Optional. Time period to wait for
            event and responses.
        :param event_subscription_check_period: (int) Time in seconds for sleep
            intervals in the event subsription thread.
        :param liveliness_check_period: (int) Period for the liveliness probe
            to monitor each device in a loop
        :param timeout : Optional. Time period to wait for
            intialization of adapter.
        """
        super().__init__(
            op_state_model,
            _input_parameter,
            logger,
            _component,
            _liveliness_probe,
            _event_receiver,
            _update_device_callback,
            _update_telescope_state_callback,
            _update_telescope_health_state_callback,
            _update_tmc_op_state_callback,
            _update_imaging_callback,
            communication_state_callback,
            _telescope_availability_callback,
            component_state_callback,
            proxy_timeout,
            event_subscription_check_period,
            liveliness_check_period,
            skuid_service,
            command_timeout,
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
        self.event_queues.update(
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

    def check_if_dishes_are_responsive(self):
        """Checks whether dishes are responsive"""
        self.logger.info("Checking if dishes are responsive")
        return self._check_if_device_is_responsive(
            self.input_parameter.dish_leaf_node_dev_names
        )

    def get_load_disg_cfg_resultcode(self):
        """Return Aggregated command result for Load Dish Cfg command"""
        return self.load_dish_cfg_aggregated_result

    @property
    def is_dish_vcc_config_set(self):
        """Getter method for is_dish_vcc_config_set"""
        return self._is_dish_vcc_config_set

    @is_dish_vcc_config_set.setter
    def is_dish_vcc_config_set(self, value):
        """Setter method for is_dish_vcc_config_set"""
        self._is_dish_vcc_config_set = value

    @property
    def dish_vcc_validation_status(self):
        """Getter method for dish vcc validation status"""
        return self._dish_vcc_validation_status

    @dish_vcc_validation_status.setter
    def dish_vcc_validation_status(self, validation_status: dict):
        """This method does the aggregation from Dish and CSPMLN
         and sets the updated validation result.
         Ex1:
         current_dish_vcc_validation_status = '{
                "d0001": "k-value not set",
                "d0036": "k-value not set",
                "d0063": "k-value not set",
                "d0100": "k-value not set",
                "mid-tmc/leaf-node-csp/0":
                "TMC and CSP Master Dish Vcc Version is Same",
            }'
         validation_status = {
                "d0001": "k-value identical",
                "d0036": "k-value identical",
                "d0063": "k-value not set",
                "d0100": "k-value not set",
         }
         if validation_status received and current validation status is
         as above then this method will aggregate like below:
         self._dish_vcc_validation_status = '{
                "d0001": "k-value identical",
                "d0036": "k-value identical",
                "d0063": "k-value not set",
                "d0100": "k-value not set",
                "mid-tmc/leaf-node-csp/0":
                "TMC and CSP Master Dish Vcc Version is Same",
            }'
        or Ex2:
         if validation_status = {"dish":"ALL DISH OK"}
         then:
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
        """This method wait for csp master leaf node and
        dish leaf nodes to become ready to accept request
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
            self.logger.debug("Current device states: %s", dev_state_list)
            count += 1
            if count == self.dish_vcc_init_timeout:
                break
        return False

    def update_long_running_command_result(self, dev_name: str, value: tuple):
        """Updates the LRCR callback with received event.

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

        :param dev_name: name of the device who's event has been
        captured in this method
        :type dev_name: str
        :param value: longRunningCommandResult attribute event.
        :type value: tuple
        """
        self.logger.info(
            "longRunningCommandResult event for device '%s'. Event value: %s",
            dev_name,
            value,
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
                    self.logger.info(
                        "Command with unique_id '%s' "
                        "on device '%s' succeeded.",
                        unique_id,
                        dev_name,
                    )
                case (
                    ResultCode.FAILED
                    | ResultCode.REJECTED
                    | ResultCode.NOT_ALLOWED
                    | ResultCode.ABORTED
                ):
                    self.logger.info(
                        "Updating LRCRCallback with result_code '%s' and "
                        "message '%s' "
                        "for command '%s' on device '%s'.",
                        result_code,
                        message,
                        unique_id,
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
                "Exception occurred while processing long running "
                "command result "
                "for device '%s': %s",
                dev_name,
                exception,
            )

    def get_command_id(self, unique_id: int) -> str:
        """This Method is used to get command
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

    def update_device_state(self, device_name, state):
        """
        Update a monitored device state,
        aggregate the states available
        and call the relative callbacks if available

        :param dev_name: name of the device
        :type dev_name: str
        :param state: state of the device
        :type state: DevState
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
        """
        return self.input_parameter.dish_leaf_node_dev_names

    def update_device_dish_mode(self, dev_name, dish_mode: DishMode) -> None:
        """
        Update the dish mode of the given dish leaf node
        and call the relative callbacks if available.
        :param dishMode: Dish mode of the device
        :type dishMode: DishMode
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

    def add_dishes(self, dln_prefix, num_dishes):
        """
        Add dishes to the liveliness probe function

        :param dln_prefix: prefix of the dish
        :type dln_prefix: str
        :param num_dishes: number of dishes
        :type num_dishes: int
        """
        result = []
        for dish in range(1, (num_dishes + 1)):
            self.add_device(f"{dln_prefix}{dish:03d}")
            result.append(f"{dln_prefix}{dish:03d}")
        return result

    def _aggregate_telescope_state(self):
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

    def _aggregate_health_state(self):
        """
        Aggregates all health states
        and call the relative callback if available
        """
        if self._health_state_aggregator is None:
            self._health_state_aggregator = HealthStateAggregatorMid(
                self, self.logger
            )

        with self.rlock:
            self.component.telescope_health_state = (
                self._health_state_aggregator.aggregate()
            )
            self.logger.debug(
                "SubarrayNode aggregated healthState: "
                + f"{HealthState(self.component.telescope_health_state).name}"
            )

    def is_command_allowed(self, command_name=None):
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the
        component needed for the operation are not unresponsive

        :param command_name: name of the command
        :type command_name: str
        :return: True if this command is allowed

        :rtype: boolean
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
                f"Command '{command_name}' is not supported "
                + f"in {self.op_state_model.op_state} for CentralNode"
            )
            raise CommandNotAllowed(
                "Command is not allowed in current state :"
                + f"{str(self.op_state_model.op_state)}",
            )
        return True

    def check_device_responsiveness(self, command_name) -> None:
        """
        This method overrides the method from super class
        to add responsive checks for the devices
        :param command_name: Command name for the check
        :type command_name: str
        """
        if command_name in self.supported_commands_for_responsive_check:
            self.logger.debug(f"Checking mid devices for {command_name}")
            self.check_if_subarrays_are_responsive()
            self.check_if_dishes_are_responsive()

    def update_k_value_validation(self, dev_name: str, kvalue: ResultCode):
        """Updates the k value validation value and starts the aggregation.

        Args:
            dev_name (str): device name
            kvalue (ResultCode): k value validation result
        """
        self.dish_kvalue_validation_aggregator.aggregate(dev_name, kvalue)

    def update_telescope_availability(self, device_name, event_value):
        """Updates telescope availablity status"""
        with self.rlock:
            if "tm_subarray_node" in device_name:
                self.subarray_availability[device_name] = event_value
            elif "tm_leaf_node/csp_master" in device_name:
                self.csp_mln_availability = event_value
            elif "tm_leaf_node/sdp_master" in device_name:
                self.sdp_mln_availability = event_value
            self._telescope_availability_aggregator.aggregate()

    def update_dish_vcc_flag(self, value: bool) -> None:
        """Update dish vcc flag and call telescope state
        aggregator
        """
        self.logger.info("Updating dish vcc config set flag to %s", value)
        self.is_dish_vcc_config_set = value
        self.update_dishvccconfig_callback(self.is_dish_vcc_config_set)
        self._aggregate_telescope_state()

    def get_default_dish_vcc_config_params(self):
        """Return default dish vcc config json"""
        return {
            "interface": DISH_VCC_CONFIG_INTERFACE_VERSION,
            "tm_data_sources": [self.dish_vcc_uri],
            "tm_data_filepath": self.dish_vcc_file_path,
        }

    def check_if_csp_all_dish_ready(self):
        """Check and validate all dish and csp master is ready"""
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
                self.logger.exception("Error %s", e)
            count += 1
            time.sleep(1)
        return False

    def handle_dish_vcc_validation_result(
        self, dev_name: str, result: ResultCode
    ) -> None:
        """Handle Dish Vcc Validation Result
        Based on following table Result codes handled and attributes updated

        Result Code | Meaning
        UNKNOWN     | Dish Vcc Config not set on CSP
        OK          | Dish Vcc Config on CSP LN and CSP match
        FAILED      | Mismatch in dish vcc version on CSP LN and CSP Master
        NOT_ALLOWED | CSP master is not available

        Result Code | Action
        UNKNOWN     | Load Dish Config using LoadDishCfg command
        OK          | Dish Vcc already set so set is_dish_vcc_config_set
        to True
        FAILED      | Dish Vcc is mismatch so set set is_dish_vcc_config_set
        to False
        NOT_ALLOWED | Set is_dish_vcc_config_set to False
        """
        self.logger.info(
            "Dish Vcc Validation Event called with dev %s and result %s",
            dev_name,
            result,
        )
        with self.dish_vcc_validation_attr_lock:
            if "tm_leaf_node/csp_master" in dev_name:
                # Handle Csp Master Leaf Node event
                csp_validation_result = int(result)
                self.logger.info(
                    "Csp Validation Result is %s", csp_validation_result
                )
                if (
                    csp_validation_result == ResultCode.UNKNOWN
                    and self.command_in_progress != "LoadDishCfg"
                ):
                    # Unknown Result code sent when no dish vcc set
                    # so invoke LoadDishCfg

                    self.command_in_progress = "LoadDishCfg"
                    if self.check_if_csp_all_dish_ready():
                        self.invoke_load_dish_cfg_command_callback()
                    else:
                        self.logger.info(
                            "Time Out while waiting for Dishes to be ready"
                        )
                        self.command_in_progress = ""
                elif (
                    csp_validation_result in DISH_VCC_VALIDATION_RESULT_STATUS
                ):
                    if csp_validation_result == ResultCode.OK:
                        self.update_dish_vcc_flag(True)
                    else:
                        self.update_dish_vcc_flag(False)
                    self.dish_vcc_validation_status = {
                        MID_CSP_MLN_DEVICE: DISH_VCC_VALIDATION_RESULT_STATUS[
                            csp_validation_result
                        ]
                    }

    def load_dish_cfg(self, argin: str, task_callback: Callable = None):
        """
        Load Dish Cfg command for Dish-VCC map.
        :param argin: Dish Id Vcc map initial params
        :return: a result code and message
        """
        loadishcfg_command = LoadDishCfg(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        try:
            dishid_vcc_map_params = json.loads(argin)
            self.logger.debug("JSON argin is in correct format.")
        except json.JSONDecodeError as e:
            self.dish_vcc_validation_status = {
                CENTRALNODE_MID: "JsonDecodeError"
            }
            return loadishcfg_command.reject_command(
                f"The JSON string is malformed. Error: {str(e)}"
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
        self.logger.info("DishId Vcc Map Json %s", dishid_vcc_map_json)
        (
            is_valid_dish_cfg,
            message,
        ) = loadishcfg_command.load_dish_config_json_validator(
            dishid_vcc_map_json
        )
        if not is_valid_dish_cfg:
            if message:
                self.dish_vcc_validation_status = {CENTRALNODE_MID: message}
            return loadishcfg_command.reject_command(message)

        task_status, response = self.submit_task(
            loadishcfg_command.load_dish_cfg,
            args=[argin, self.logger],
            task_callback=task_callback,
        )
        return task_status, response

    def update_load_dish_cfg_results_async(
        self, dev_name: str, value: tuple
    ) -> None:
        """This method is used to update the result returned
        from Csp Master Leaf Node
        and returned from Dish Leaf Nodes for SetKValue command.
        :param dev_name: name of the device who's event has been
        captured in this method
        :type dev_name: str
        :param value: longRunningCommandResult attribute event.
        :type value: tuple

        """
        self.update_load_dish_cfg_results(
            dev_name, value, is_async_result=True
        )

    def update_load_dish_cfg_results(
        self, dev_name: str, value: tuple, is_async_result: bool = False
    ) -> None:
        """This method is used to update the result returned
        from Csp Master Leaf Node
        and returned from Dish Leaf Nodes for SetKValue command.
        Update result_codes_mapping with dev name as a key and
        command result as a value
        If all events are received from all device then aggregate
        the result
        Value contains (unique_id, ResultCode) or (unique_id,exception_msg)
        or (unique_id,TaskStatus)
        :param dev_name: name of the device who's event has been
        captured in this method
        :type dev_name: str
        :param value: longRunningCommandResult attribute event.
        :type value: tuple
        :param is_async_result: Whether this callback is called
        from Async command result call or
        longRunningCommandResult attribute callback
        Examples of value
        Async callback value: [array([0], dtype=int32), ['']]
        LongRunningCommandResultCallBack value:
        ('1698838234.9087641-LoadDishCfg',
        'Exception occurred, command failed.')
        """
        self.logger.info(
            "longRunningCommandResult event for device: %s, with value: %s",
            dev_name,
            value,
        )
        with self.rlock:
            result_code_or_exception = []
            if is_async_result:
                # Set result code and message
                self.logger.debug(
                    "event from asynchronous command result callback %s",
                    value,
                )
                result_code_or_exception = [value[0][0], value[1][0]]

            else:
                self.logger.debug(
                    "event from long command result callback %s",
                    value,
                )
                unique_id, resultcode_message = value
                self.logger.debug(
                    f"unique id {unique_id}," + f"{resultcode_message}"
                )
                if unique_id.endswith("LoadDishCfg"):
                    result_code_or_exception = json.loads(resultcode_message)
            if result_code_or_exception and self.dev_names_for_load_dish_cfg:
                self.result_codes_mapping[dev_name] = result_code_or_exception
                self.logger.info(
                    "Dev names for load_dish_cfg values %s "
                    + "and result_codes_mapping are %s",
                    self.dev_names_for_load_dish_cfg,
                    self.result_codes_mapping,
                )

            # When all events received from dishes and Csp master leaf node
            # then aggregate the result
            if len(self.dev_names_for_load_dish_cfg) == len(
                self.result_codes_mapping
            ):
                # Aggregate the result
                self.logger.info(
                    "All Events received for load dish cfg Aggregating results"
                )
                self.aggregate_load_dish_cfg_results()

    def aggregate_load_dish_cfg_results(self) -> None:
        """This method aggregate load dish cfg command result based on
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

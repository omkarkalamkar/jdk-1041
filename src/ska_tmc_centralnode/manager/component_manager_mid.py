"""
This module is inherited from CNComponentManager.

It is component Manager for Mid Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import json
import threading
import time

from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode, LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from ska_tmc_centralnode.manager.aggregators import (
    DishkValueValidationResultAggregator,
    HealthStateAggregatorMid,
    TelescopeAvailabilityAggregatorMid,
    TelescopeStateAggregatorMid,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.utils.constants import (
    DISH_VCC_CONFIG_INTERFACE_VERSION,
    DISH_VCC_VALIDATION_RESULT_STATUS,
    MID_CSP_MLN_DEVICE,
)


class CNComponentManagerMid(CNComponentManager):
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
        communication_state_callback=None,
        component_state_callback=None,
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
        skuid_service="",
        command_timeout=30,
        dish_vcc_uri=None,
        dish_vcc_file_path=None,
        dish_vcc_init_timeout=120,
        dishKvalueAggregationAllowedPercent=100.0,
        invoke_load_dish_cfg_command_callback=None,
        enable_dish_vcc_init=True,
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
        :param sleep_time: Optional. Sleep time between reties.
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
            component_state_callback,
            _telescope_availability_callback,
            max_workers,
            proxy_timeout,
            sleep_time,
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
        self._dish_vcc_validation_status = "{}"
        self.dish_vcc_validation_attr_lock = threading.Lock()
        self.enable_dish_vcc_init = enable_dish_vcc_init

    def check_if_dishes_are_responsive(self):
        self.logger.info("Checking if dishes are responsive")
        return self._check_if_device_is_responsive(
            self.input_parameter.dish_leaf_node_dev_names
        )

    @property
    def is_dish_vcc_config_set(self):
        return self._is_dish_vcc_config_set

    @is_dish_vcc_config_set.setter
    def is_dish_vcc_config_set(self, value):
        self._is_dish_vcc_config_set = value

    @property
    def dish_vcc_validation_status(self):
        return self._dish_vcc_validation_status

    @dish_vcc_validation_status.setter
    def dish_vcc_validation_status(self, temp_dict):
        """ """
        csp_value = ""
        new_value = temp_dict.copy()
        existing_value = json.loads(self._dish_vcc_validation_status)
        # Extract existing CSPMLN result
        if MID_CSP_MLN_DEVICE in existing_value:
            csp_value = {
                MID_CSP_MLN_DEVICE: existing_value[MID_CSP_MLN_DEVICE]
            }

        # If all Dish are set, remove all other instances
        if "dish" in new_value:
            # Overwrite the results
            existing_value = new_value
            self.is_dish_vcc_config_set = True
            if csp_value:
                if (
                    csp_value[MID_CSP_MLN_DEVICE]
                    != DISH_VCC_VALIDATION_RESULT_STATUS[ResultCode.OK]
                ):
                    self.is_dish_vcc_config_set = False

                existing_value.update(csp_value)
        else:
            # If the event from dish only
            if MID_CSP_MLN_DEVICE not in new_value:
                # Remove dish value from existing value
                existing_value.pop("dish", None)
                # Overwrite the results
                existing_value = new_value
                if csp_value:
                    existing_value.update(csp_value)
            else:
                # If the event from CSPMLN only
                existing_value.update(new_value)
        self._dish_vcc_validation_status = json.dumps(
            {
                key: value
                for key, value in existing_value.items()
                if value != "k-value identical"
            }
        )
        # empty the dictionaries
        existing_value = {}
        new_value = {}

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
            self.logger.info("Device State List %s", dev_state_list)
            count += 1
            if count == self.dish_vcc_init_timeout:
                break
        return False

    def update_long_running_command_result(self, dev_name: str, value: tuple):
        """Updates the LRCR callback with received event.

        Value contains (unique_id, ResultCode) or (unique_id,exception_msg) or (unique_id,TaskStatus)
        Whenever there is exception occured , (unique_id,exception_msg) event is first raised
        and catched in ValueError.The exception_msg and command_id is then passed to long_running_result_callback.
        Command_mapping contains {centralnode_command_id:unique_id} , all events are verified with respect to this mapping.
        If there is no command_mapping present the event might be of old command.

        :param dev_name: name of the device who's event has been captured in this method
        :type dev_name: str
        :param value: longRunningCommandResult attribute event.
        :type value: tuple
        """
        self.logger.info(
            "Received longRunningCommandResult event for device: %s, with value: %s",
            dev_name,
            value,
        )
        unique_id, result_code_or_exception_or_task_status = value
        if unique_id.endswith(
            self.supported_commands
        ):  # ignoring other command events
            try:
                self.logger.info(
                    f"LongRunningCommandResult event occurred: {result_code_or_exception_or_task_status}"
                )

                if not result_code_or_exception_or_task_status:
                    # This is in case an empty event is received.
                    pass
                elif (
                    int(result_code_or_exception_or_task_status)
                    == ResultCode.OK
                    and unique_id in self.command_mapping.values()
                ):
                    # Update the command_result only if it's "AssignResources" or "ReleaseResources" and successful.
                    self.command_result = ResultCode.OK

            except ValueError:
                if unique_id in self.command_mapping.values():
                    self.logger.info(
                        "Updating LRCRCallback with value: %s for %s for device: %s",
                        unique_id,
                        value,
                        dev_name,
                    )
                    exception_message = f"Exception occurred on device: {dev_name}: {result_code_or_exception_or_task_status}"
                    index_of_unique_id = list(
                        self.command_mapping.values()
                    ).index(
                        unique_id
                    )  # get index location of unique_id received in event
                    command_id = list(self.command_mapping.keys())[
                        index_of_unique_id
                    ]  # command id mapped to unique id
                    self.long_running_result_callback(
                        command_id,
                        ResultCode.FAILED,
                        exception_msg=exception_message,
                    )

    def update_device_state(self, dev_name, state):
        """
        Update a monitored device state,
        aggregate the states available
        and call the relative callbacks if available

        :param dev_name: name of the device
        :type dev_name: str
        :param state: state of the device
        :type state: DevState
        """
        with self.lock:
            self.logger.info(
                f"State event callback for device {dev_name}: {state}"
            )
            if "sdp" in dev_name:
                # Update SDP Master device name with full FQDN in case of real SDP
                sdp_master_dev_name = self.get_sdp_master_dev_name()
                if dev_name in sdp_master_dev_name:
                    dev_name = sdp_master_dev_name
            if "csp" in dev_name:
                # Update CSP Master device name with full FQDN in case of real CSP
                csp_master_dev_name = self.get_csp_master_dev_name()
                if dev_name in csp_master_dev_name:
                    dev_name = csp_master_dev_name
            if "elt/master" in dev_name:
                # Update Dish Master device name with full FQDN in case of real Dish
                dish_master_dev_names = self.get_dish_device_names()
                for dish in dish_master_dev_names:
                    if dev_name in dish:
                        dev_name = dish

            devInfo = self.component.get_device(dev_name)
            if devInfo is not None:
                devInfo.state = state
                devInfo.last_event_arrived = time.time()
                devInfo.update_unresponsive(False)
                self.component._invoke_device_callback(devInfo)

        self._aggregate_state()
        self._update_imaging()

    def update_device_dish_mode(self, dev_name, dish_mode: DishMode) -> None:
        """
        Update the dish mode of the given dish and call
        the relative callbacks if available.
        :param dishMode: Dish mode of the device
        :type dishMode: DishMode
        """

        with self.lock:
            self.logger.info(
                f"Dish event callback for device {dev_name}: {dish_mode}"
            )

            # Update Dish Master device name with full FQDN in case of real Dish
            dish_master_dev_names = self.get_dish_device_names()
            for dish in dish_master_dev_names:
                if dev_name in dish:
                    dev_name = dish

            dev_info = self.component.get_device(dev_name)
            dev_info.dish_mode = dish_mode
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
            self.add_device(dln_prefix + "{:03d}".format(dish))
            result.append(dln_prefix + "{:03d}".format(dish))
        return result

    def _aggregate_telescope_state(self):
        """
        Aggregates telescope state
        """
        if self._telescope_state_aggregator is None:
            self._telescope_state_aggregator = TelescopeStateAggregatorMid(
                self, self.logger
            )

        with self.lock:
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

        with self.lock:
            self.component.telescope_health_state = (
                self._health_state_aggregator.aggregate()
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
                    "Dish Vcc Config not Set. Please set using LoadDishCfg command. "
                    "Current Telescope State is %s",
                    str(self.op_state_model.op_state),
                )
        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                "Command is not allowed in current state %s",
                str(self.op_state_model.op_state),
            )
        if command_name in ["TelescopeOn", "TelescopeOff", "TelescopeStandby"]:
            self.logger.debug(f"Checking mid devices for {command_name}")
            self.check_if_subarrays_are_responsive()
            self.check_if_dishes_are_responsive()
        elif command_name in ["AssignResources", "ReleaseResources"]:
            self.logger.info(f"Checking mid devices for {command_name}")
            self.check_if_subarrays_are_responsive()
            self.check_if_dishes_are_responsive()

        return True

    def update_telescope_availability(self, device_name, event_value):
        with self.lock:
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
        self._aggregate_telescope_state()

    def get_default_dish_vcc_config_params(self):
        """Return default dish vcc config json"""
        return {
            "interface": DISH_VCC_CONFIG_INTERFACE_VERSION,
            "tm_data_sources": [self.dish_vcc_uri],
            "tm_data_filepath": self.dish_vcc_file_path,
        }

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
        OK          | Dish Vcc already set so set is_dish_vcc_config_set to True
        FAILED      | Dish Vcc is mismatch so set set is_dish_vcc_config_set to False
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
                if csp_validation_result == ResultCode.UNKNOWN:
                    """Unknown Result code sent when no dish vcc set
                    so invoke LoadDishCfg
                    """
                    self.invoke_load_dish_cfg_command_callback()
                elif (
                    csp_validation_result
                    in DISH_VCC_VALIDATION_RESULT_STATUS.keys()
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

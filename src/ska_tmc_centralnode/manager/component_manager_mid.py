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

from ska_control_model import AdminMode, TaskStatus
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.faults import StateModelError
from ska_tmc_common import AdapterType
from ska_tmc_common.enum import DishMode, LivelinessProbeType
from ska_tmc_common.exceptions import CommandNotAllowed, InvalidReceptorIdError
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command_mid import (
    AssignResourcesMid,
)
from ska_tmc_centralnode.commands.release_resources_command_mid import (
    ReleaseResourcesMid,
)
from ska_tmc_centralnode.commands.set_global_pointing_model import (
    SetGlobalPointingModel,
)
from ska_tmc_centralnode.commands.stow_antennas_command import SetStowMode
from ska_tmc_centralnode.input_validator import (
    AssignResourceValidator,
    ReleaseResourceValidator,
)
from ska_tmc_centralnode.manager.aggregate_process import (
    HealthStateAggregationProcessor,
)
from ska_tmc_centralnode.manager.aggregators import (
    DishAttrValueAggregator,
    TelescopeAvailabilityAggregatorMid,
    TelescopeStateAggregatorMid,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.manager.gpm_json_model import GPMJsonModel
from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.refactored_commands.load_dish_cfg.contexts import (
    CommandContext,
    DeviceContext,
    LoadDishCfgRuntimeContext,
)

# pylint:disable=line-too-long
from ska_tmc_centralnode.refactored_commands.load_dish_cfg.load_dish_config_command import (
    LoadDishCfg,
)
from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_MID,
    DISH_VCC_CONFIG_INTERFACE_VERSION,
    DISH_VCC_VALIDATION_RESULT_STATUS,
    MID_CSP_MLN_DEVICE,
)

# pylint:disable=too-many-instance-attributes
# pylint:disable=too-many-arguments


class CNComponentManagerMid(CNComponentManager):
    """Component manager class for central node mid"""

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        op_state_model,
        _input_parameter,
        logger: Logger,
        _dish_vcc_command_status_callback: Callable,
        _update_device_callback: Callable,
        _update_telescope_state_callback: Callable,
        _update_telescope_health_state_callback: Callable,
        _update_tmc_op_state_callback: Callable,
        _update_imaging_callback: Callable,
        _telescope_availability_callback: Callable,
        array_layout_url_callback: Callable,
        default_array_layout_url_callback: Callable,
        _update_dishvccconfig_callback: Callable,
        _dishvccvalidation_callback: Callable,
        _component=None,
        _liveliness_probe=LivelinessProbeType.MULTI_DEVICE,
        _event_manager=True,
        proxy_timeout=500,
        event_subscription_check_period=1,
        liveliness_check_period=1,
        command_timeout=30,
        dish_vcc_uri=None,
        dish_vcc_file_path=None,
        dish_vcc_init_timeout=120,
        dishKvalueAggregationAllowedPercent=100.0,
        invoke_load_dish_cfg_command_callback=None,
        invoke_set_gpm_command_callback=None,
        enable_dish_vcc_init=True,
        k_value_valid_range_upper_limit=1177,
        k_value_valid_range_lower_limit=1,
        subarray_trl_prefix: str = "mid-tmc/subarray/",
        gpm_version=None,
        gpm_interface=None,
        gpm_data_sources_prefix=None,
        gpm_file_path_prefix=None,
        default_array_layout_url: dict | None = None,
        mkt_extension_id: str = "",
        mkt_dish_ranges: tuple[int, int] = (0, 63),
        ska_dish_ranges: tuple[int, int] = (1, 999),
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
            invoke_set_gpm_command_callback:
                callback for set GPM command
            enable_dish_vcc_init:
                enable dish vcc
            k_value_valid_range_upper_limit:
                k value upper limit
            k_value_valid_range_lower_limit:
                k value lower limit.
            gpm_version: GPM version
            gpm_interface: GPM interface,
            gpm_data_sources_prefix: GPM data sources prefix path,
            gpm_file_path_prefix: GPM file path prefix,

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
            array_layout_url_callback,
            default_array_layout_url_callback,
            _component,
            _liveliness_probe,
            _event_manager,
            proxy_timeout,
            event_subscription_check_period,
            liveliness_check_period,
            command_timeout,
            subarray_trl_prefix=subarray_trl_prefix,
            default_array_layout_url=default_array_layout_url,
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
        self.set_telescope_availability(telescope_availability)

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
        self.invoke_set_gpm_command_callback = invoke_set_gpm_command_callback
        self.dishKvalueAggregationAllowedPercent = (
            dishKvalueAggregationAllowedPercent
        )
        self.dish_kvalue_validation_aggregator = DishAttrValueAggregator(
            self, self.logger
        )
        self.dev_names_for_load_dish_cfg = []
        self.dishln_gpm_cmd_exe_data = (
            {}
        )  # dishln_gpm_data_created_during_command_execution
        self.load_dish_cfg_aggregated_result = None
        self.gpm_version_aggregated_result = ResultCode.UNKNOWN
        self.gpm_aggregated_result = True
        self.load_dish_cfg_command_id = None
        self._dish_vcc_validation_status = "{}"
        self._global_pointing_model_status = {}
        self.dish_vcc_validation_attr_lock = threading.Lock()
        self.dishln_gpm_lock = threading.RLock()
        self.dishln_gpm_command_lock = threading.RLock()
        self.enable_dish_vcc_init = enable_dish_vcc_init
        self.command_result = None
        self.k_value_valid_range_upper_limit = k_value_valid_range_upper_limit
        self.k_value_valid_range_lower_limit = k_value_valid_range_lower_limit
        self.update_dishvccconfig_callback = _update_dishvccconfig_callback
        self.dishvccvalidation_callback = _dishvccvalidation_callback
        self._dish_vcc_command_status = DishConfigStatus.STAGING
        self.dish_vcc_command_status_callback = (
            _dish_vcc_command_status_callback
        )
        self.number_of_gpm_executed = 0
        self.gpm_unknown_dishes = []
        self.gpm_version = gpm_version
        self.gpm_interface = gpm_interface
        self.gpm_data_sources_prefix = gpm_data_sources_prefix
        self.gpm_file_path_prefix = gpm_file_path_prefix
        self.is_gpm_init = True
        self.dishln_stow_mode_lock = threading.RLock()
        self.number_of_stow_mode_executed: int = 0
        self.mkt_extension_id = mkt_extension_id
        self.mkt_dish_ranges = mkt_dish_ranges
        self.ska_dish_ranges = ska_dish_ranges
        self.stow_mode_command_aggregated_result: ResultCode = (
            ResultCode.UNKNOWN
        )
        self.stow_mode_aggregated_result: bool = True
        self.dishln_stow_mode_cmd_exe_data: dict = {}
        self.event_queue.update(
            {
                "dishMode": Queue(),
                "kValueValidationResult": Queue(),
                "DishVccMapValidationResult": Queue(),
                "isSubsystemAvailable": Queue(),
                "isSubarrayAvailable": Queue(),
                "state": Queue(),
                "gpmVersion": Queue(),
            }
        )
        handle_dish_vcc = self.handle_dish_vcc_validation_result
        self.event_processing_methods.update(
            {
                "dishMode": self.update_device_dish_mode,
                "kValueValidationResult": self.update_k_value_validation,
                "DishVccMapValidationResult": handle_dish_vcc,
                "isSubsystemAvailable": self.update_telescope_availability,
                "isSubarrayAvailable": self.update_telescope_availability,
                "state": self.update_device_state,
                "gpmVersion": self.handle_gpm_version_event,
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

    # pylint:enable=too-many-arguments

    def check_if_dishes_are_responsive(self) -> bool:
        """
        Checks whether dishes are responsive

        Returns:
            True, if dishes are responsive,
            False otherwise

        """
        self.logger.debug("Checking if dishes are responsive")
        return self._check_if_device_is_responsive(
            self.input_parameter.dish_leaf_node_dev_names
        )

    def get_set_gpm_version_resultcode(self) -> ResultCode:
        """
        Return Aggregated command result for Set GPM Version command

        Returns:
            Aggregated command result for Set GPM Version command

        """
        return self.gpm_version_aggregated_result

    def get_set_stow_mode_resultcode(self) -> ResultCode:
        """
        Return Aggregated command result for Set Stow Mode command

        Returns:
            Aggregated command result(ResultCode) for Set Stow Mode command

        """
        return self.stow_mode_command_aggregated_result

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

    @property
    def global_pointing_model_status(self) -> dict:
        """
        Getter method for dish GPM version status

        Returns:
            dish: dish GPM version status

        """
        return self._global_pointing_model_status

    @global_pointing_model_status.setter
    def global_pointing_model_status(self, gpm_version: dict):
        """
        This method does the aggregation from Dish
        and sets the updated GPM version.
        """
        self._global_pointing_model_status = gpm_version

    def is_csp_mln_csp_master_ready(self) -> str:
        """
        This method wait for csp master leaf node and
        csp_master to become ready to accept request

        Returns:
            True, if csp master leaf node and
            dish leaf nodes are ready, False otherwise

        """
        count = 0
        while count <= self.dish_vcc_init_timeout:
            try:
                count += 2
                time.sleep(2)
                csp_mln_adapter = self.adapter_factory.get_or_create_adapter(
                    self.input_parameter.csp_mln_dev_name,
                    adapter_type=AdapterType.CSP_MASTER_LEAF_NODE,
                )
                csp_master_adapter = (
                    self.adapter_factory.get_or_create_adapter(
                        self.input_parameter.csp_master_dev_name,
                        adapter_type=AdapterType.CSPMASTER,
                    )
                )
                self.logger.debug(
                    "CSP MLN version: %s CSP master state: %s",
                    csp_mln_adapter._proxy.GetVersionInfo(),
                    csp_master_adapter.state,
                )

                if csp_master_adapter.state != DevState.OFF:
                    return ResultCode.NOT_ALLOWED
                return ResultCode.OK
            except Exception as e:
                self.logger.exception("Error %s", str(e))
        return ResultCode.FAILED

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
                    break
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

    def is_valid_admin_mode(self) -> bool:
        """
        Validates that all relevant subarray devices are in a valid admin mode.

        Returns:
            bool: True if all subarrays are in a valid mode, False otherwise.


        """
        sdp_admin_mode = self.get_sdp_controller_admin_mode()
        csp_admin_mode = self.get_csp_controller_admin_mode()

        admin_modes = [sdp_admin_mode, csp_admin_mode]

        if any(
            mode in [AdminMode.OFFLINE, AdminMode.NOT_FITTED]
            for mode in admin_modes
        ):
            self.logger.debug(
                "AdminMode check failed: SDP=%s, CSP=%s",
                sdp_admin_mode,
                csp_admin_mode,
            )
            return False
        return True

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
        if not self.is_valid_admin_mode():
            raise CommandNotAllowed(
                "One or more controller devices are in "
                "adminMode OFFLINE or NOT-FITTED"
            )

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
            self.logger.warning(
                f"{command_name} command is not supported "
                + f"in {self.op_state_model.op_state} for CentralNode"
            )
            raise CommandNotAllowed(
                "Command is not allowed in current state :"
                + f"{str(self.op_state_model.op_state)}",
            )
        return True

    def check_device_responsiveness_command(
        self, command_name: str, subarray_id: int
    ) -> None:
        """
        This method overrides the method from super class
        to add responsive checks for the devices

        Args:
            command_name (str): Command name for the check
            subarray_id (int): Subarray id

        """
        super().check_device_responsiveness_command(command_name, subarray_id)
        if command_name in self.supported_commands_for_responsive_check:
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

    def get_default_gpm_version_params(self) -> dict:
        """
        Return default GPM version parameters

        Returns:
            Default GPM version parameters

        """
        return {
            "version": self.gpm_version,
            "interface": self.gpm_interface,
            "tm_data_sources": [self.gpm_data_sources_prefix],
            "tm_data_filepath": self.gpm_file_path_prefix,
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
                    self.logger.debug(
                        "All dishes and csp master devices are"
                        " available and ready."
                    )
                    return True
            except Exception as e:
                self.logger.exception("Error %s", str(e))
            count += 1
            time.sleep(1)

        # If Any of the dish leaf node is available
        # execute LoadDishCfg command.
        if len(num_of_dish_values):
            return True

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
                    and self.command_in_progress != "LoadDishCfg"
                ):
                    # Unknown Result code sent when no dish vcc set
                    # so invoke LoadDishCfg

                    self.command_in_progress = "LoadDishCfg"
                    if self.check_if_csp_all_dish_ready():
                        self.dish_vcc_command_status = DishConfigStatus.INIT
                        self.invoke_load_dish_cfg_command_callback()
                    else:
                        self.logger.warning(
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

            with self.command_completion_cond:
                self.command_completion_cond.notify_all()

    def update_kval_aggregator(self, dish_id: str, error_message: str) -> None:
        """
        Update the k-value validation aggregator with the error message
        for the given dish ID.
        """
        with self.dish_vcc_validation_attr_lock:
            aggregator = self.dish_kvalue_validation_aggregator
            val_results = aggregator.dln_kvalue_validation_results
            val_results[dish_id.lower()] = error_message

    def append_dish_dev_names(self, dish_dev_name: str) -> None:
        """
        Append dish device names to the list of dishes for LoadDishCfg command

        Args:
            dish_dev_name (str): Dish device name

        """
        if dish_dev_name not in self.dev_names_for_load_dish_cfg:
            self.dev_names_for_load_dish_cfg.append(dish_dev_name)

    def _get_load_dish_cfg_context(self) -> LoadDishCfgRuntimeContext:
        """
        Get the context for LoadDishCfg command
        Returns:
            dict: LoadDishCfg command context
        """
        device_ctx = DeviceContext(
            csp_mln_device_name=self.input_parameter.csp_mln_dev_name,
            dish_leaf_node_dev_names=self.get_dish_leaf_node_device_names(),
            get_dev=self.get_device,
        )
        command_ctx = CommandContext(
            command_timeout=self.command_timeout,
            update_command_in_progress_id=lambda command_name: setattr(
                self, "command_in_progress", command_name
            ),
            set_load_dish_cfg_aggregated_result=lambda result: setattr(
                self, "load_dish_cfg_aggregated_result", result
            ),
            set_dish_vcc_command_status=lambda status: setattr(
                self, "dish_vcc_command_status", status
            ),
            update_dish_vcc_flag=self.update_dish_vcc_flag,
            get_dish_vcc_validation_status=lambda: self.dish_vcc_validation_status,
            set_dish_vcc_validation_status=lambda status: setattr(
                self, "dish_vcc_validation_status", status
            ),
        )
        return LoadDishCfgRuntimeContext(
            device_ctx=device_ctx,
            command_ctx=command_ctx,
            append_dish_dev_names=self.append_dish_dev_names,
            update_kval_aggregator=self.update_kval_aggregator,
            dish_kvalue_validation_aggregator=self.dish_kvalue_validation_aggregator,
        )

    # pylint: disable=unexpected-keyword-arg
    def load_dish_cfg(
        self, argin: str, task_callback: Callable, task_abort_event
    ) -> Tuple[ResultCode, str]:
        """
        Load Dish Cfg command for Dish-VCC map.

        Args:
            argin (str): Dish Id Vcc map initial params

        Returns:
            a result code and message

        """

        status = self.is_csp_mln_csp_master_ready()
        if status != ResultCode.OK:
            if status == ResultCode.NOT_ALLOWED:
                err_msg = (
                    "LoadDishCfg command is allowed in"
                    " CSP Master DevState.OFF only."
                )
            else:
                err_msg = (
                    "CSP master or CSP MLN is not available for"
                    " loaddishcfg execution"
                )
            self.update_dish_vcc_flag(False)
            return task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, err_msg),
            )
        loadishcfg_command_object = LoadDishCfg(
            self._get_load_dish_cfg_context(),
            adapter_factory=self.adapter_factory,
            logger=self.logger,
        )
        self.logger.debug(
            "Command Status: %s ",
            str(DishConfigStatus(self.dish_vcc_command_status).name),
        )

        try:
            json.loads(argin)
            self.logger.debug("JSON argin is in correct format.")
        except json.JSONDecodeError as e:
            self.dish_vcc_validation_status = {
                CENTRALNODE_MID: "JsonDecodeError"
            }
            message = f"The JSON string is malformed. Error: {str(e)}"
            return task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, message),
            )

        return loadishcfg_command_object.execute(
            argin=argin,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def set_gpm_version(
        self, argin: str, task_callback: Callable, task_abort_event
    ) -> Tuple[ResultCode, str]:
        """
        Set GPM version for Dish.

        Args:
            argin (str): Dish Id's with the specified bands and version.

        Returns:
            a result code and message

        """

        keys_to_allow_skip = [
            "version",
            "tm_data_filepath",
            "tm_data_sources",
            "interface",
        ]
        set_gpm_version_command_object = SetGlobalPointingModel(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        try:
            gpm_input = json.loads(argin)
            self.logger.debug(
                "GPM JSON argin is in correct format. %s", gpm_input
            )
            if not all(key in gpm_input for key in keys_to_allow_skip):
                GPMJsonModel(**gpm_input)
                if not self.validate_dish_ids(gpm_input["receptors"].keys()):
                    raise InvalidReceptorIdError(
                        f"Incorrect receptor id in json: {gpm_input}"
                    )
            else:
                self.logger.debug(
                    "Executing initialization/restart SetGPM on %s",
                    self.gpm_unknown_dishes,
                )

            return set_gpm_version_command_object.apply_gpm(
                dish_gpm_params=argin,
                logger=self.logger,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )
        except Exception as exception:
            self.logger.exception("Exception occured %s", exception)
            return task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )

    def set_stow_mode(
        self, argin: str, task_callback: Callable, task_abort_event
    ) -> Tuple[ResultCode, str]:
        """
        Set stow mode for given dishes.

        Args:
            argin (str): Dish Id's.

        Returns:
            a result code and message

        """

        set_stow_mode_command_object = SetStowMode(
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        try:
            messgae = "Invalid input: Expected a list of dish IDs"
            example = 'e.g., ["ska001", "ska002", ...] or ["ALL"]'
            stow_input = json.loads(argin)
            if not isinstance(stow_input, list):
                raise ValueError(messgae + " " + example)
            if "ALL" in stow_input:
                if len(stow_input) == 1:
                    stow_input = []
                    for dish_id in self.get_dish_leaf_node_device_names():
                        stow_input.append(dish_id.rsplit("/", 1)[-1])
                else:
                    raise ValueError(messgae + " " + example)
            self.validate_dish_ids(stow_input)
            stow_input = [dish_id.lower() for dish_id in stow_input]
            self.logger.debug("Stow command dish list: %s", stow_input)
            return set_stow_mode_command_object.apply_stow_mode(
                argin=stow_input,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )
        except Exception as exception:
            self.logger.exception("Exception occured %s", exception)
            return task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )

    # pylint: enable=unexpected-keyword-arg

    def reset_load_dish_cfg_data(self) -> None:
        """Reset all data which is set for aggregating LoadDisgCfg command"""
        self.logger.debug("Resetting LoadDishCfg aggregated data")
        self.load_dish_cfg_aggregated_result = ""
        self.dev_names_for_load_dish_cfg = []
        self.result_codes_mapping = {}
        self.load_dish_cfg_command_id = None
        self.command_in_progress = ""
        self._check_init_and_invoke_gpm()

    def _check_init_and_invoke_gpm(self):
        """If TMC is in initalization phase then invoke gpm"""
        if self.is_gpm_init and self.invoke_set_gpm_command_callback:
            self.invoke_set_gpm_command_callback()
            self.is_gpm_init = False

    def handle_gpm_version_event(
        self, dev_name: str, gpmVersion: dict
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
            "GPM versions received %s from %s", gpmVersion, dev_name
        )
        with self.dishln_gpm_lock:
            dish_id = dev_name.split("/")[-1]
            self.global_pointing_model_status[dish_id] = json.loads(gpmVersion)
            if self.check_if_csp_all_dish_ready():
                gpm_aggregator = DishAttrValueAggregator(self, self.logger)
                self.gpm_unknown_dishes = gpm_aggregator.aggregate_gpm()
                self.logger.debug(
                    "Command in progress %s and Dish-Vcc command status %s",
                    self.command_in_progress,
                    self._dish_vcc_command_status,
                )
                if self.gpm_unknown_dishes and not self.command_in_progress:
                    if (
                        self._dish_vcc_command_status
                        == DishConfigStatus.COMPLETED
                    ):
                        self.logger.info(
                            "Restart phase: Invoking Set GPM command on:  %s",
                            self.gpm_unknown_dishes,
                        )
                        self.invoke_set_gpm_command_callback()

    def reset_gpm_data(self) -> None:
        """Reset GPM data"""

        self.logger.debug("Resetting SetGlobalPointingModel data")
        self.gpm_version_aggregated_result = ResultCode.UNKNOWN
        self.number_of_gpm_executed = 0
        self.dishln_gpm_cmd_exe_data = {}
        self.gpm_unknown_dishes = []
        self.command_in_progress = ""
        if self.command_mapping.get(self.command_id):
            self.command_mapping.pop(self.command_id)

    def _get_band_dishln_gpm_cmd_data(self, unique_id: str) -> str:
        """Return Band for the specified dish in unique id
        Args:
            unique_id: command unique id
        Returns:
            band (str)
        """
        band = ""
        for command_data in self.command_mapping[self.command_id]:
            if unique_id in command_data:
                band = command_data[unique_id]
        return band

    def reset_stow_mode_data(self) -> None:
        """Reset StowMode data"""
        self.logger.debug("Resetting SetStowMode data")
        self.stow_mode_command_aggregated_result = ResultCode.UNKNOWN
        self.number_of_stow_mode_executed = 0
        self.dishln_stow_mode_cmd_exe_data = {}
        self.command_in_progress = ""
        if self.command_mapping.get(self.command_id):
            self.command_mapping.pop(self.command_id)

    def get_current_dish_mode_of_dln(self, dish_id: str) -> DishMode:
        """
        Get the current dish mode of the specified dish leaf node.

        Args:
            dish_id (str): Dish identifier to retrieve mode for

        Returns:
            DishMode: Current mode of the specified dish

        """
        dish_leaf_node_dev_names = self.get_dish_leaf_node_device_names()
        dish_dev_name = ""
        for dish in dish_leaf_node_dev_names:
            if dish_id in dish:
                dish_dev_name = dish
                break
        dev_info = self.component.get_device(dish_dev_name)
        return dev_info.dish_mode

    def check_timeout_for_stow_mode_lrcr_events(self) -> bool:
        """Check timeout error in dishln_stow_mode_cmd_exe_data dictionary"""
        for (
            dish_id,
            result_code_or_exception,
        ) in self.dishln_stow_mode_cmd_exe_data.items():
            if isinstance(result_code_or_exception, str):
                continue
            result_code = result_code_or_exception.get("result_code", [])
            _, message = result_code if len(result_code) == 2 else (None, "")
            if "timeout" in message.lower():
                self.logger.debug(
                    "%s: %s",
                    dish_id,
                    result_code_or_exception["result_code"],
                )
                self.set_dish_mode_in_stow_mode_cmd_exe_data()
                self.stow_mode_aggregated_result = False
                return True
        return False

    def set_dish_mode_in_stow_mode_cmd_exe_data(self) -> None:
        """ "Set dish mode in stow mode command execution data dictionary."""
        for dish_id, data in self.dishln_stow_mode_cmd_exe_data.items():
            if isinstance(data, dict):
                data["dish_mode"] = DishMode(
                    self.get_current_dish_mode_of_dln(dish_id)
                ).name

    def validate_assign_json(self, argin: str) -> Tuple[str, str]:
        """Validates assign resources json

        :param argin: json input
        :type argin: str

        :return: Returns the original argument and exception message.
        :rtype: tuple[str, str]
        """
        exception_msg: str = ""
        try:
            json_argument = json.loads(argin)
            self.validate_subarray_id(json_argument)
            # Utilize CDM to validate json.
            available_subarrays_list = self.input_parameter.subarray_dev_names
            dish_leaf_node_prefix = self.input_parameter.dish_leaf_node_prefix
            available_dish_leaf_node_devices = (
                self.input_parameter.dish_leaf_node_dev_names
            )
            assign_validator = AssignResourceValidator(
                available_subarrays_list,
                available_dish_leaf_node_devices,
                dish_leaf_node_prefix,
                self.logger,
                self.mkt_extension_id,
                self.ska_dish_ranges,
                self.mkt_dish_ranges,
            )

            assign_validator.loads(argin)
        except Exception as exception:
            exception_msg = str(exception)
            self.logger.exception(
                "Exception occurred while processing assignresource: %s ",
                exception_msg,
            )
        return argin, exception_msg

    # pylint: disable=unexpected-keyword-arg
    def assign_resources(
        self, argin, task_callback: TaskCallbackType, task_abort_event
    ) -> Tuple[TaskStatus, str]:
        """
        Submits the AssignResources command in queue.

        :param argin: input json string for assign resource command
        :type argin: str
        :param task_callback: Update task state, defaults to None
        :type task_callback: TaskCallbackType
        :param task_abort_event: Event to abort the task
        :type task_abort_event: Event
        :return: task_status
        :rtype: tuple
        """
        try:
            k_value_failed_dishes = {}
            # Execute the command if the input JSON is valid
            self.logger.debug(
                "Calling component manager assign_resources method"
            )
            receptors = (
                json.loads(argin).get("dish", {}).get("receptor_ids", [])
            )
            k_value_status = json.loads(self.dish_vcc_validation_status)

            for d in receptors:
                dish = d.lower()
                if dish in k_value_status:
                    k_value_failed_dishes[dish] = k_value_status[dish]

            if k_value_failed_dishes:
                err_msg = (
                    "Can't assign receptors with k-value issues:"
                    f" {k_value_failed_dishes}"
                )
                self.logger.debug(
                    "Dish k-value STATUS: %s, receptors assigned: %s",
                    k_value_status,
                    receptors,
                )
                return task_callback(
                    status=TaskStatus.REJECTED,
                    result=(ResultCode.NOT_ALLOWED, err_msg),
                )
            assign_resources_command_object = AssignResourcesMid(
                self,
                adapter_factory=self.adapter_factory,
                logger=self.logger,
            )
            assign_resources_command_object.subarray_id = self.get_subarray_id(
                argin
            )
            # Validate command is allowed
            self.is_command_allowed_before_lrc_start(
                subarray_id=assign_resources_command_object.subarray_id,
                command_name="AssignResources",
            )

            return assign_resources_command_object.assign_resources(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        except (StateModelError, CommandNotAllowed) as exception:
            self.logger.exception(
                "Exception occurred while processing " + "assignresource: %s ",
                exception,
            )
            return task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )

        except Exception as exception:
            self.logger.exception(
                "Exception occurred while processing " + "assignresource: %s ",
                exception,
            )
            return task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, str(exception)),
            )

    # pylint: enable=unexpected-keyword-arg

    def validate_release_json(self, argin: str) -> Tuple[str, str]:
        """Validates the release resource json.

        :param argin: release resource json string.
        :type argin: str

        :return: Returns the original argument and exception message.
        :rtype: tuple[str, str]
        """
        exception_msg: str = ""
        try:
            json_argument = json.loads(argin)
            self.validate_subarray_id(json_argument)
            release_validator = ReleaseResourceValidator(self.logger)
            release_validator.loads(argin)

        except Exception as exception:
            exception_msg = str(exception)
            self.logger.exception(
                "Exception occurred while processing releaseresource: %s ",
                exception_msg,
            )
        return argin, exception_msg

    # pylint: disable=unexpected-keyword-arg
    def release_resources(
        self, argin: str, task_callback: TaskCallbackType, task_abort_event
    ) -> Tuple[TaskStatus, str]:
        """
        Submit the ReleaseResource command in queue.

        :param argin: input json string for release resource command
        :type argin: str
        :param task_callback: Updates task status
        :type task_callback: TaskCallbackType
        :param task_abort_event: Event to abort the task
        :type task_abort_event: Event
        :return: task_status
        :rtype: tuple
        """
        try:
            release_resources_command_object = ReleaseResourcesMid(
                self, adapter_factory=self.adapter_factory, logger=self.logger
            )

            self.check_availability_for_release(argin)
            release_resources_command_object.subarray_id = (
                self.get_subarray_id(argin)
            )
            # Validate command is allowed
            self.is_command_allowed_before_lrc_start(
                subarray_id=release_resources_command_object.subarray_id,
                command_name="ReleaseResources",
            )
            return release_resources_command_object.release_resources(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        except (StateModelError, CommandNotAllowed) as exception:
            self.logger.exception(
                "Exception occurred while processing "
                + "releaseresource: %s ",
                exception,
            )
            return task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )

        except Exception as exception:
            self.logger.exception(
                "Exception occurred while processing "
                + "releaseresource: %s ",
                exception,
            )
            return task_callback(
                status=TaskStatus.COMPLETED,
                result=(ResultCode.FAILED, str(exception)),
            )

    # pylint: enable=unexpected-keyword-arg

    def validate_dish_ids(self, receptors: list[str]) -> bool:
        """Validates dish ids."""
        for dish_id in receptors:
            dish_id = dish_id.upper()
            if dish_id.startswith("SKA"):
                dish_suffix = int(dish_id[3:])
                if (self.ska_dish_ranges[1] < dish_suffix) or (
                    dish_suffix < self.ska_dish_ranges[0]
                ):
                    return False, f"Dish id {dish_id} not in range (1,999)"
            elif dish_id.startswith("MKT"):
                dish_suffix = int(dish_id[3:])
                if (self.mkt_dish_ranges[1] < dish_suffix) or (
                    dish_suffix < self.mkt_dish_ranges[0]
                ):
                    return False, f"MKT id {dish_id} not in range (1,63)"
            elif not (
                self.mkt_extension_id
                and dish_id.startswith(self.mkt_extension_id)
            ):
                return False, f"Invalid Dish id {dish_id} provided in Json"
        return True, ""

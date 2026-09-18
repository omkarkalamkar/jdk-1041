"""
This module is inherited from CNComponentManager.

It is component Manager for Mid Telecope.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import copy
import json
import threading
import time
from typing import Callable, Dict, List, Tuple, Union, cast

from ska_control_model import TaskStatus
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.software_bus import Signal
from ska_tmc_common import (
    AdapterType,
    DeviceInfo,
    DishDeviceInfo,
    SubArrayDeviceInfo,
)
from ska_tmc_common.enum import DishMode
from tango import DevState

from ska_tmc_centralnode.input_validator import (
    AssignResourceValidator,
    ReleaseResourceValidator,
)
from ska_tmc_centralnode.manager.aggregate_process import (
    HealthStateAggregationProcessor,
)
from ska_tmc_centralnode.manager.aggregators import (
    DishAttrValueAggregator,
    TelescopeAvailabilityAggregator,
    TelescopeStateAggregatorMid,
)
from ska_tmc_centralnode.manager.command_allowance_validator import (
    MidCommandAllowanceValidator,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.manager.component_manager_config import (
    MidCentralNodeComponentManagerConfig,
)
from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.refactored_commands.assignresources import (
    ArrayLayoutContext,
    CommandInProgressContext,
    MidAssignResourcesContext,
    ObsStateContext,
)
from ska_tmc_centralnode.refactored_commands.load_dish_cfg.contexts import (
    DeviceContext,
    LoadDishCfgCommandContext,
    LoadDishCfgRuntimeContext,
)

# pylint:disable=line-too-long
from ska_tmc_centralnode.refactored_commands.load_dish_cfg.load_dish_config_command import (
    LoadDishCfg,
)
from ska_tmc_centralnode.refactored_commands.releaseresources import (
    MidReleaseResourcesContext,
    ReleaseResourcesMid,
)
from ska_tmc_centralnode.refactored_commands.set_gpm.contexts import GPMContext
from ska_tmc_centralnode.refactored_commands.set_gpm.set_gpm_command import (
    SetGlobalPointingModel,
)
from ska_tmc_centralnode.refactored_commands.set_stow_mode.contexts import (
    StowContext,
)
from ska_tmc_centralnode.refactored_commands.set_stow_mode.set_stow_command import (
    SetStowMode,
)

# pylint:enable=line-too-long
from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_MID,
    DISH_VCC_CONFIG_INTERFACE_VERSION,
    DISH_VCC_VALIDATION_RESULT_STATUS,
    MID_CSP_MLN_DEVICE,
)

from ..model.input import InputParameterMid
from ..refactored_commands.assignresources import assign_resources_command_mid
from ..utils.exception_decorator import exception_handler
from .event_callback_manager.mid_event_callback_manager import (
    MidEventCallbackContext,
    MidEventCallbackManager,
)
from .event_processor import MidEventProcessor

AssignResourcesMid = assign_resources_command_mid.AssignResourcesMid

# pylint:disable=too-many-instance-attributes
# pylint:disable=too-many-arguments


class CNComponentManagerMid(CNComponentManager[InputParameterMid]):
    """Component manager class for central node mid"""

    _is_dish_vcc_config_set: Signal[bool] = Signal[bool](
        stored=True, initial_value=False
    )
    _dish_vcc_command_status: Signal[DishConfigStatus] = Signal[
        DishConfigStatus
    ](stored=True, initial_value=DishConfigStatus.STAGING)
    _dish_vcc_validation_status: Signal[str] = Signal[str](
        stored=True, initial_value="{}"
    )
    _global_pointing_model_status: Signal[dict] = Signal[dict](
        stored=True, initial_value={}
    )

    def __init__(self, config: MidCentralNodeComponentManagerConfig) -> None:
        """
        Initialise a new ComponentManager instance for mid.

        Args:
           config: Instance of MidCentralNodeComponentManagerConfig.

        """
        super().__init__(config)
        self.config = config
        self.csp_mln_availability = False
        self.sdp_mln_availability = False

        self._telescope_availability_aggregator = (
            TelescopeAvailabilityAggregator(self, self.logger)
        )
        self.dish_kvalue_validation_aggregator = DishAttrValueAggregator(
            self, self.logger
        )
        self.gpm_aggregator = DishAttrValueAggregator(self, self.logger)
        self.dev_names_for_load_dish_cfg: List[str] = []
        # dishln_gpm_data_created_during_command_execution
        self.dishln_gpm_cmd_exe_data: Dict[str, str] = {}
        self.gpm_version_aggregated_result = ResultCode.UNKNOWN
        self.gpm_aggregated_result = True
        self.load_dish_cfg_command_id = None
        self.dish_vcc_validation_attr_lock = threading.Lock()
        self.dishln_gpm_lock = threading.RLock()
        self.dishln_gpm_command_lock = threading.RLock()
        self.command_result = None
        self.number_of_gpm_executed = 0
        self.gpm_unknown_dishes: List[str] = []
        self.is_gpm_init = True
        self.event_processor: MidEventProcessor = MidEventProcessor(
            stop_event=self._stop_thread,
            logger=config.logger,
            on_error=self.update_event_failure,
        )
        self._event_cb_manager: MidEventCallbackManager = (
            self._get_event_cb_manager()
        )
        self._register_event_handlers(self._get_event_handlers())
        self.event_processor.start()
        # start the aggregation process
        self.aggregation_process = HealthStateAggregationProcessor(
            self.event_data_queue,
            self.aggregated_health_state,
            self.aggregate_value_update_event,
            telescope="mid",
        )
        self.aggregation_process.start_aggregation_process()
        self.cmd_allowed_validator = MidCommandAllowanceValidator(
            logger=config.logger,
            input_parameter=config.input_parameter,
            subarray_trl_prefix=config.subarray_trl_prefix,
            retry_attempts=config.retry_attempts,
            retry_delay=config.retry_delay,
            adapter_factory=self.adapter_factory,
            get_op_state_model=lambda: self.config.op_state_model,
            dish_vcc_init_enabled=self.config.dish_config.enable_init,
            get_dish_vcc_config_set=lambda: self.is_dish_vcc_config_set,
            get_device=self.get_device,
        )

    def _get_event_cb_manager(self) -> MidEventCallbackManager:
        """Provides Instance Event Callaback Manager"""
        return MidEventCallbackManager(
            context=MidEventCallbackContext(
                **self.get_event_cb_manager_context(),
                kvalue_validation_aggregator=(
                    self.dish_kvalue_validation_aggregator
                ),
                gpm_aggregator=self.gpm_aggregator,
                update_dish_vcc_flag=self.update_dish_vcc_flag,
                _telescope_availability_aggregator=(
                    self._telescope_availability_aggregator
                ),
                update_subarray_availability=self.update_subarray_availability,
                set_csp_mln_availability=lambda availability: setattr(
                    self, "csp_mln_availability", availability
                ),
                set_sdp_mln_availability=lambda availability: setattr(
                    self, "sdp_mln_availability", availability
                ),
                gpm_invoke_command_callback=(
                    self.config.gpm_config.invoke_command_callback
                ),
                get_dish_vcc_command_status=(
                    lambda: self.dish_vcc_command_status
                ),
                dish_vcc_init_timeout=self.config.dish_config.init_timeout,
                get_command_in_progress=lambda: self.command_in_progress,
                set_command_in_progress=lambda cmd: setattr(
                    self, "command_in_progress", cmd
                ),
                set_dish_vcc_cmd_validation_status=lambda status: setattr(
                    self, "dish_vcc_validation_status", status
                ),
                set_dish_vcc_command_status=lambda status: setattr(
                    self, "dish_vcc_command_status", status
                ),
                set_global_pointing_model_status=lambda status: setattr(
                    self, "global_pointing_model_status", status
                ),
                gpm_unknown_dishes=self.gpm_unknown_dishes,
                dish_vcc_command_invoke_cb=(
                    self.config.dish_config.invoke_command_callback
                ),
                adapter_factory=self.adapter_factory,
                check_if_csp_all_dish_ready=self.check_if_csp_all_dish_ready,
            )
        )

    def create_device_info(
        self, device_name: str
    ) -> Union[SubArrayDeviceInfo, DishDeviceInfo, DeviceInfo]:
        """Creates the device information for device.

        :param device_name: Name of device.
        :type device_name: str
        :return: DeviceInfo Instance
        :rtype: SubArrayDeviceInfo or DeviceInfo or DishDeviceInfo
        """
        dev_info: SubArrayDeviceInfo = super().create_device_info(device_name)
        if (
            not dev_info
            and device_name in self.get_dish_leaf_node_device_names()
        ):
            dev_info = DishDeviceInfo(device_name, False)
        elif not dev_info:
            dev_info = DeviceInfo(device_name, False)

        return dev_info

    def get_dish_device_names(self) -> List[str]:
        """
        Return Dish Master device names
        """

        return self.input_parameter.dish_dev_names

    def get_dish_leaf_node_device_names(self) -> List[str]:
        """
        Return Dish leaf node device names
        """
        return self.input_parameter.dish_leaf_node_dev_names

    def _get_event_handlers(self) -> dict:
        """Returns event handlers with addition of mid specific.

        :return: Dictionary with attribute name and its event handler.
        :rtype: dict
        """
        event_handlers: dict = super()._get_event_handlers()
        event_handlers.update(
            {
                "dishMode": self._event_cb_manager.update_device_dish_mode,
                "kValueValidationResult": (
                    self._event_cb_manager.update_k_value_validation
                ),
                "DishVccMapValidationResult": (
                    self._event_cb_manager.handle_dish_vcc_validation_result
                ),
                "isSubsystemAvailable": (
                    self._event_cb_manager.update_telescope_availability
                ),
                "isSubarrayAvailable": (
                    self._event_cb_manager.update_telescope_availability
                ),
                "state": self._event_cb_manager.update_device_state,
                "gpmVersion": self._event_cb_manager.handle_gpm_version_event,
            }
        )
        return event_handlers

    def get_set_gpm_version_resultcode(self) -> ResultCode:
        """
        Return Aggregated command result for Set GPM Version command

        Returns:
            Aggregated command result for Set GPM Version command

        """
        return self.gpm_version_aggregated_result

    @property
    def dish_vcc_command_status(self) -> DishConfigStatus:
        """Return dish vcc command status"""
        return self._dish_vcc_command_status

    @dish_vcc_command_status.setter
    def dish_vcc_command_status(self, value: DishConfigStatus) -> None:
        """Set dish vcc command status and invoke callback"""
        self.logger.debug("Setting dish config status %s", str(value))
        self._dish_vcc_command_status = value

    @property
    def is_dish_vcc_config_set(self) -> bool:
        """Getter method for is_dish_vcc_config_set"""
        return self._is_dish_vcc_config_set

    @is_dish_vcc_config_set.setter
    def is_dish_vcc_config_set(self, value: bool) -> None:
        """Setter method for is_dish_vcc_config_set"""
        self._is_dish_vcc_config_set = value

    @property
    def dish_vcc_validation_status(self) -> str:
        """
        Getter method for dish vcc validation status

        Returns:
            dish: dish vcc validation status

        """
        return self._dish_vcc_validation_status

    @dish_vcc_validation_status.setter
    def dish_vcc_validation_status(self, validation_status: dict) -> None:
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
        csp_validation_status: Dict = {}
        # Copying here as dictionary is getting passed by reference.
        updated_validation_status = validation_status.copy()
        current_dish_vcc_validation_status: Dict[str, str] = json.loads(
            self._dish_vcc_validation_status
        )
        # Extract existing CSPMLN result
        if MID_CSP_MLN_DEVICE in current_dish_vcc_validation_status:
            csp_validation_status = {
                MID_CSP_MLN_DEVICE: current_dish_vcc_validation_status.get(
                    MID_CSP_MLN_DEVICE
                )
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
        elif (
            CENTRALNODE_MID in updated_validation_status
            or MID_CSP_MLN_DEVICE in updated_validation_status
        ):
            current_dish_vcc_validation_status.update(
                updated_validation_status
            )
        elif MID_CSP_MLN_DEVICE not in updated_validation_status:
            # Remove dish value from existing value
            current_dish_vcc_validation_status.pop("dish", None)
            # Overwrite the results
            current_dish_vcc_validation_status = updated_validation_status
            if csp_validation_status:
                current_dish_vcc_validation_status.update(
                    csp_validation_status
                )
        self._dish_vcc_validation_status = json.dumps(
            {
                key: value
                for key, value in current_dish_vcc_validation_status.items()
                if value != "k-value identical"
            }
        )

    @property
    def global_pointing_model_status(self) -> dict:
        """
        Getter method for dish GPM version status

        Returns:
            dish: dish GPM version status

        """
        return copy.deepcopy(self._global_pointing_model_status)

    @global_pointing_model_status.setter
    def global_pointing_model_status(self, gpm_version: dict) -> None:
        """
        This method does the aggregation from Dish
        and sets the updated GPM version.
        """
        model_status = self.global_pointing_model_status
        model_status.update(gpm_version)
        self._global_pointing_model_status = model_status

    def is_csp_mln_csp_master_ready(self) -> ResultCode:
        """
        This method wait for csp master leaf node and
        csp_master to become ready to accept request

        Returns:
            True, if csp master leaf node and
            dish leaf nodes are ready, False otherwise

        """
        start_time = time.time()
        while (
            time.time() - start_time
        ) <= self.config.dish_config.init_timeout:
            try:
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
                    csp_mln_adapter.proxy.GetVersionInfo(),
                    csp_master_adapter.state,
                )

                if csp_master_adapter.state != DevState.OFF:
                    return ResultCode.NOT_ALLOWED
                return ResultCode.OK
            except Exception as e:
                self.logger.exception("Error %s", str(e))
        return ResultCode.FAILED

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
            self._telescope_state_aggregator: TelescopeStateAggregatorMid = (
                TelescopeStateAggregatorMid(self, self.logger)
            )

        with self.rlock:
            new_state = self._telescope_state_aggregator.aggregate()
            self.component.telescope_state = new_state

    def stop_aggregation_process(self) -> None:
        """Stop aggregation process"""
        self.aggregation_process.stop_aggregation_process()

    def update_dish_vcc_flag(self, value: bool) -> None:
        """
        Update dish vcc flag and call telescope state
        aggregator

        Args:
            value (bool): Value of the dish vcc config flag

        """
        self.logger.debug("Updating dish vcc config set flag to %s", value)
        self.is_dish_vcc_config_set = value
        self._aggregate_telescope_state()

    def get_default_dish_vcc_config_params(self) -> dict:
        """
        Return default dish vcc config json

        Returns:
            Default dish vcc config json

        """
        return {
            "interface": DISH_VCC_CONFIG_INTERFACE_VERSION,
            "tm_data_sources": [self.config.dish_config.uri],
            "tm_data_filepath": self.config.dish_config.file_path,
        }

    def get_default_gpm_version_params(self) -> dict:
        """
        Return default GPM version parameters

        Returns:
            Default GPM version parameters

        """
        return {
            "version": self.config.gpm_config.version,
            "tm_data_sources": [self.config.gpm_config.data_sources_prefix],
            "tm_data_filepath": self.config.gpm_config.file_path_prefix,
        }

    def check_if_csp_all_dish_ready(self) -> bool:
        """
        Check and validate all dish and csp master is ready

        Returns:
            `True`, if all dish and csp master is ready,
            `False`, otherwise.

        """
        start_time = time.time()
        num_of_dish_values = {}
        # This loop keep checking for kvalueValidationResult values
        # from all dishes which confirm that event is received from
        # all dishes
        while (
            time.time() - start_time
        ) <= self.config.dish_config.init_timeout:
            try:
                for dish_name in self.input_parameter.dish_leaf_node_dev_names:
                    if dish_name not in num_of_dish_values:
                        adapter = self.adapter_factory.get_or_create_adapter(
                            dish_name, adapter_type=AdapterType.DISH
                        )
                        k_val_result = adapter.proxy.kValueValidationResult
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
            time.sleep(1)
        # If Any of the dish leaf node is available
        # execute LoadDishCfg command.
        if len(num_of_dish_values):
            return True

        return False

    def update_kval_aggregator(self, dish_id: str, error_message: str) -> None:
        """
        Update the k-value validation aggregator with the error message
        for the given dish ID.
        Args:
            dish_id: Dish Id
            error_message: error message
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

    def update_memorized_attribute(self, dish_vcc_config):
        """
        Update the memorized attribute for the component manager
        """
        csp_mln_adapter = self.adapter_factory.get_or_create_adapter(
            self.input_parameter.csp_mln_dev_name,
            AdapterType.CSP_MASTER_LEAF_NODE,
        )
        csp_mln_adapter.memorizedDishVccMap = dish_vcc_config

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
        command_ctx = LoadDishCfgCommandContext(
            command_timeout=self.config.timeout_config.command_timeout,
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
            get_dish_vcc_validation_status=(
                lambda: self.dish_vcc_validation_status
            ),
            set_dish_vcc_validation_status=lambda status: setattr(
                self, "dish_vcc_validation_status", status
            ),
            update_memorized_attribute=self.update_memorized_attribute,
            reset_load_dish_cfg_data=self.reset_load_dish_cfg_data,
        )
        return LoadDishCfgRuntimeContext(
            command_completion_condition=self.command_completion_cond,
            device_ctx=device_ctx,
            command_ctx=command_ctx,
            append_dish_dev_names=self.append_dish_dev_names,
            update_kval_aggregator=self.update_kval_aggregator,
            dish_kvalue_validation_aggregator=(
                self.dish_kvalue_validation_aggregator
            ),
            k_value_valid_range_lower_limit=(
                self.config.dish_config.k_value_valid_range_lower_limit
            ),
            k_value_valid_range_upper_limit=(
                self.config.dish_config.k_value_valid_range_upper_limit
            ),
            validate_dish_ids=self.validate_dish_ids,
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

        set_gpm_version_command_object = SetGlobalPointingModel(
            command_runtime_context=self._get_gpm_context(),
            adapter_provider=self.adapter_factory,
            logger=self.logger,
        )

        return set_gpm_version_command_object.execute(
            argin=argin,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    def _get_gpm_context(self) -> GPMContext:
        """Get the SetGlobalPointingModel command context.

        :return: SetGlobalPointingModel command context.
        :rtype: GPMContext
        """
        return GPMContext(
            command_completion_condition=self.command_completion_cond,
            command_timeout=self.config.timeout_config.command_timeout,
            update_name=lambda name: setattr(
                self, "command_in_progress", name
            ),
            clear=lambda: setattr(self, "command_in_progress", ""),
            get_name=lambda: self.command_in_progress,
            gpm_unknown_dishes=self.gpm_unknown_dishes,
            dishln_gpm_cmd_exe_data=self.dishln_gpm_cmd_exe_data,
            is_already_assigned=self.is_already_assigned,
            default_gpm_version_params=self.get_default_gpm_version_params(),
            update_abort_evt=lambda evt: setattr(self, "abort_event", evt),
            get_dish_leaf_node_device_names=(
                self.get_dish_leaf_node_device_names
            ),
            get_device=self.get_device,
            dish_leaf_node_prefix=self.input_parameter.dish_leaf_node_prefix,
            dishln_gpm_lock=self.dishln_gpm_lock,
            global_pointing_model_status=self.global_pointing_model_status,
            reset_gpm_data=self.reset_gpm_data,
        )

    def _get_stow_context(self) -> StowContext:
        """Build StowContext bound to this component manager.

        :return: Runtime context for SetStowMode command execution.
        :rtype: StowContext
        """
        return StowContext(
            command_completion_condition=self.command_completion_cond,
            command_timeout=self.config.timeout_config.command_timeout,
            cmd_inprogress_ctx=CommandInProgressContext(
                update_name=lambda name: setattr(
                    self, "command_in_progress", name
                ),
                clear=lambda _: setattr(self, "command_in_progress", ""),
                get_name=lambda: self.command_in_progress,
            ),
            update_abort_evt=lambda evt: setattr(self, "abort_event", evt),
            dish_leaf_node_prefix=self.input_parameter.dish_leaf_node_prefix,
            get_current_dish_mode_of_dln=self.get_current_dish_mode_of_dln,
        )

    def set_stow_mode(
        self, argin: str, task_callback: Callable, task_abort_event
    ) -> None:
        """
        Set stow mode for given dishes.

        Args:
            argin (str): Dish Id's.

        Returns:
            a result code and message

        """

        set_stow_mode_command_object = SetStowMode(
            self._get_stow_context(),
            adapter_provider=self.adapter_factory,
            logger=self.logger,
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
            set_stow_mode_command_object.execute(
                argin=stow_input,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )
        except Exception as exception:
            self.logger.exception("Exception occured %s", exception)
            task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, str(exception)),
            )

    def reset_load_dish_cfg_data(self) -> None:
        """Reset all data which is set for aggregating LoadDisgCfg command"""
        self.logger.debug("Resetting LoadDishCfg aggregated data")
        self.dev_names_for_load_dish_cfg = []
        self.load_dish_cfg_command_id = None
        self.command_in_progress = ""
        self._check_init_and_invoke_gpm()

    def _check_init_and_invoke_gpm(self) -> None:
        """If TMC is in initalization phase then invoke gpm"""
        if self.is_gpm_init and self.config.gpm_config.invoke_command_callback:
            self.config.gpm_config.invoke_command_callback()
            self.is_gpm_init = False

    def reset_gpm_data(self) -> None:
        """Reset GPM data"""

        self.logger.debug("Resetting SetGlobalPointingModel data")
        self.dishln_gpm_cmd_exe_data = {}
        self.gpm_unknown_dishes = []
        self.command_in_progress = ""

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
        dish_mode = DishMode.UNKNOWN
        for dish in dish_leaf_node_dev_names:
            if dish_id in dish:
                dish_dev_name = dish
                break
        if dish_dev_name:
            dev_info = cast(
                DishDeviceInfo, self.component.get_device(dish_dev_name)
            )
            dish_mode = cast(DishMode, dev_info.dish_mode)
        return dish_mode

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
            available_dish_leaf_node_devices = (
                self.input_parameter.dish_leaf_node_dev_names
            )
            assign_validator = AssignResourceValidator(
                available_subarrays_list,
                available_dish_leaf_node_devices,
                self.logger,
                self.config.mkt_extension_id,
                self.config.ska_dish_ranges,
                self.config.mkt_dish_ranges,
            )

            assign_validator.loads(argin)
        except Exception as exception:
            exception_msg = str(exception)
            self.logger.exception(
                "Exception occurred while processing assignresource: %s ",
                exception_msg,
            )
        return argin, exception_msg

    def _get_assign_context(self) -> MidAssignResourcesContext:
        """Build MidAssignResourcesContext bound to this component manager.

        :return: Runtime context for AssignResources command execution.
        :rtype: MidAssignResourcesContext
        """
        return MidAssignResourcesContext(
            command_completion_condition=self.command_completion_cond,
            command_timeout=self.config.timeout_config.command_timeout,
            cmd_inprogress_ctx=CommandInProgressContext(
                update_name=lambda name: setattr(
                    self, "command_in_progress", name
                ),
                clear=lambda _: setattr(self, "command_in_progress", ""),
                get_name=lambda: self.command_in_progress,
            ),
            array_layout_ctx=ArrayLayoutContext(
                update_url=lambda url: setattr(self, "array_layout_url", url),
                get_default_url=lambda: self.default_array_layout_url,
            ),
            obs_state_ctx=ObsStateContext(get=self.get_subarray_obsstate),
            input_parameter=self.input_parameter,
            update_abort_evt=lambda evt: setattr(self, "abort_event", evt),
            log_state=self.log_state,
            subarray_trl_prefix=self.config.subarray_trl_prefix,
            is_already_assigned=self.is_already_assigned,
        )

    def _get_release_context(self) -> MidReleaseResourcesContext:
        """Build MidReleaseResourcesContext bound to this component manager."""
        return MidReleaseResourcesContext(
            command_completion_condition=self.command_completion_cond,
            cmd_inprogress_ctx=CommandInProgressContext(
                update_name=lambda name: setattr(
                    self, "command_in_progress", name
                ),
                clear=lambda _: setattr(self, "command_in_progress", ""),
                get_name=lambda: self.command_in_progress,
            ),
            command_timeout=self.config.timeout_config.command_timeout,
            input_parameter=self.input_parameter,
            update_abort_evt=lambda evt: setattr(self, "abort_event", evt),
            obs_state_ctx=ObsStateContext(get=self.get_subarray_obsstate),
            subarray_trl_prefix=self.config.subarray_trl_prefix,
        )

    @exception_handler(command_name="AssignResources")
    def assign_resources(
        self, argin, task_callback: TaskCallbackType, task_abort_event
    ) -> None:
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

        k_value_failed_dishes = {}
        # Execute the command if the input JSON is valid
        receptors = json.loads(argin).get("dish", {}).get("receptor_ids", [])
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
            task_callback(
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, err_msg),
            )
            return
        assign_resources_command_object = AssignResourcesMid(
            adapter_provider=self.adapter_factory,
            logger=self.logger,
            command_runtime_context=self._get_assign_context(),
        )
        assign_resources_command_object.subarray_id = self.get_subarray_id(
            argin
        )
        # Validate command is allowed
        self.cmd_allowed_validator.is_command_allowed_before_lrc_start(
            subarray_id=assign_resources_command_object.subarray_id,
            command_name="AssignResources",
        )

        assign_resources_command_object.execute(
            argin=argin,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

    @exception_handler(command_name="ReleaseResources")
    def release_resources(
        self, argin: str, task_callback: TaskCallbackType, task_abort_event
    ) -> None:
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
        release_resources_command_object = ReleaseResourcesMid(
            adapter_provider=self.adapter_factory,
            logger=self.logger,
            command_runtime_context=self._get_release_context(),
        )

        self.check_availability_for_release(argin)
        release_resources_command_object.subarray_id = self.get_subarray_id(
            argin
        )
        # Validate command is allowed
        self.cmd_allowed_validator.is_command_allowed_before_lrc_start(
            subarray_id=release_resources_command_object.subarray_id,
            command_name="ReleaseResources",
        )
        release_resources_command_object.execute(
            argin=argin,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

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

    def validate_dish_ids(self, receptors: list[str]) -> Tuple[bool, str]:
        """Validates dish ids."""
        for dish_id in receptors:
            dish_id = dish_id.upper()
            if dish_id.startswith("SKA"):
                dish_suffix = int(dish_id[3:])
                if (self.config.ska_dish_ranges[1] < dish_suffix) or (
                    dish_suffix < self.config.ska_dish_ranges[0]
                ):
                    return False, f"Dish id {dish_id} not in range (1,999)"
            elif dish_id.startswith("MKT"):
                dish_suffix = int(dish_id[3:])
                if (self.config.mkt_dish_ranges[1] < dish_suffix) or (
                    dish_suffix < self.config.mkt_dish_ranges[0]
                ):
                    return False, f"MKT id {dish_id} not in range (1,63)"
            elif not (
                self.config.mkt_extension_id
                and dish_id.startswith(self.config.mkt_extension_id)
            ):
                return False, f"Invalid Dish id {dish_id} provided in Json"
        return True, ""

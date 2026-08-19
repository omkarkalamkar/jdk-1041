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
from typing import Callable, Dict, List, Tuple, cast

from ska_control_model import TaskStatus
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.software_bus import Signal
from ska_tmc_common import AdapterType, DeviceInfo
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import InvalidReceptorIdError
from tango import DevState

from ska_tmc_centralnode.commands.assign_resources_command_mid import (
    AssignResourcesMid,
)
from ska_tmc_centralnode.commands.load_dish_config_command import LoadDishCfg
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
from ska_tmc_centralnode.manager.command_allowance_validator import (
    MidCommandAllowanceValidator,
)
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.manager.component_manager_config import (
    MidCentralNodeComponentManagerConfig,
)
from ska_tmc_centralnode.manager.gpm_json_model import GPMJsonModel
from ska_tmc_centralnode.model.enum import DishConfigStatus
from ska_tmc_centralnode.utils.constants import (
    CENTRALNODE_MID,
    DISH_VCC_CONFIG_INTERFACE_VERSION,
    DISH_VCC_VALIDATION_RESULT_STATUS,
    MID_CSP_MLN_DEVICE,
)

from ..utils.exception_decorator import exception_handler
from .event_callback_manager.mid_event_callback_manager import (
    MidEventCallbackManager,
)
from .event_processor import MidEventProcessor

# pylint:disable=too-many-instance-attributes
# pylint:disable=too-many-arguments


class CNComponentManagerMid(CNComponentManager):
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

    # pylint:disable=keyword-arg-before-vararg
    def __init__(self, config: MidCentralNodeComponentManagerConfig) -> None:
        """
        Initialise a new ComponentManager instance for mid.

        Args:
           config:

        """
        super().__init__(config)
        self.config = config
        self.subarray_availability = {
            subarray: False
            for subarray in self.input_parameter.subarray_dev_names
        }
        self.csp_mln_availability = False
        self.sdp_mln_availability = False

        self._telescope_availability_aggregator = (
            TelescopeAvailabilityAggregatorMid(self, self.logger)
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
        self.dishln_stow_mode_lock = threading.RLock()
        self.number_of_stow_mode_executed: int = 0
        self.stow_mode_command_aggregated_result: ResultCode = (
            ResultCode.UNKNOWN
        )
        self.stow_mode_aggregated_result: bool = True
        self.dishln_stow_mode_cmd_exe_data: dict = {}
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
            logger=self.logger,
            component=self.component,
            command_completion_cond=self.command_completion_cond,
            input_parameter=self.input_parameter,
            event_data_manager=self.event_data_manager,
            _aggregate_state=self._aggregate_state,
            kvalue_validation_aggregator=(
                self.dish_kvalue_validation_aggregator
            ),
            gpm_aggregator=self.gpm_aggregator,
            update_dish_vcc_flag=self.update_dish_vcc_flag,
            _telescope_availability_aggregator=(
                self._telescope_availability_aggregator
            ),
            subarray_availability=self.subarray_availability,
            set_csp_mln_availability=lambda availability: setattr(
                self, "csp_mln_availability", availability
            ),
            set_sdp_mln_availability=lambda availability: setattr(
                self, "sdp_mln_availability", availability
            ),
            gpm_invoke_command_callback=(
                self.config.gpm_config.invoke_command_callback
            ),
            get_dish_vcc_command_status=lambda: self.dish_vcc_command_status,
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

    @property
    def is_dish_vcc_config_set(self):
        """Getter method for is_dish_vcc_config_set"""
        return self._is_dish_vcc_config_set

    @is_dish_vcc_config_set.setter
    def is_dish_vcc_config_set(self, value):
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
        return copy.deepcopy(self._global_pointing_model_status)

    @global_pointing_model_status.setter
    def global_pointing_model_status(self, gpm_version: dict):
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
        count = 0
        while count <= self.config.dish_config.init_timeout:
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
                    csp_mln_adapter.proxy.GetVersionInfo(),
                    csp_master_adapter.state,
                )

                if csp_master_adapter.state != DevState.OFF:
                    return ResultCode.NOT_ALLOWED
                return ResultCode.OK
            except Exception as e:
                self.logger.exception("Error %s", str(e))
        return ResultCode.FAILED

    def get_dish_leaf_node_device_names(self) -> tuple:
        """
        Return Dish leaf node device names

        Returns:
            A tuple of dish leaf node devices names

        """
        return self.input_parameter.dish_leaf_node_dev_names

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
            "interface": self.config.gpm_config.interface,
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
        count = 0
        num_of_dish_values = {}
        # This loop keep checking for kvalueValidationResult values
        # from all dishes which confirm that event is received from
        # all dishes
        while count <= self.config.dish_config.init_timeout:
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
            count += 1
            time.sleep(1)

        # If Any of the dish leaf node is available
        # execute LoadDishCfg command.
        if len(num_of_dish_values):
            return True

        return False

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
            self, adapter_factory=self.adapter_factory, logger=self.logger
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

        return loadishcfg_command_object.load_dish_cfg(
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
        self.dev_names_for_load_dish_cfg = []
        self.load_dish_cfg_command_id = None
        self.command_in_progress = ""
        self._check_init_and_invoke_gpm()

    def _check_init_and_invoke_gpm(self):
        """If TMC is in initalization phase then invoke gpm"""
        if self.is_gpm_init and self.config.gpm_config.invoke_command_callback:
            self.config.gpm_config.invoke_command_callback()
            self.is_gpm_init = False

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
        command_mapping = cast(
            Dict[str, List[Dict[str, str]]], self.command_mapping
        )
        for command_data in command_mapping.get(self.command_id, {}):
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
        dev_info = cast(DeviceInfo, self.component.get_device(dish_dev_name))
        return cast(DishMode, dev_info.dish_mode)

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
        self.logger.debug("Calling component manager assign_resources method")
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
            self,
            adapter_factory=self.adapter_factory,
            logger=self.logger,
        )
        assign_resources_command_object.subarray_id = self.get_subarray_id(
            argin
        )
        # Validate command is allowed
        self.cmd_allowed_validator.is_command_allowed_before_lrc_start(
            subarray_id=assign_resources_command_object.subarray_id,
            command_name="AssignResources",
        )

        assign_resources_command_object.assign_resources(
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
            self, adapter_factory=self.adapter_factory, logger=self.logger
        )

        self.check_availability_for_release(argin)
        subarray_id = self.get_subarray_id(argin)
        release_resources_command_object.subarray_id = str(subarray_id)
        # Validate command is allowed
        self.cmd_allowed_validator.is_command_allowed_before_lrc_start(
            subarray_id=subarray_id,
            command_name="ReleaseResources",
        )
        release_resources_command_object.release_resources(
            argin=argin,
            task_callback=task_callback,
            task_abort_event=task_abort_event,
        )

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

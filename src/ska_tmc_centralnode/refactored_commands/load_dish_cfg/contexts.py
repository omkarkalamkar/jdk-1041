"""
Contains the runtime context classes for the LoadDishCfg command.
"""
from dataclasses import dataclass
from typing import Any, Callable

from ska_tmc_common.v4.command_context import CommandRuntimeContext


@dataclass(kw_only=True)
class DishAggregationContext:
    """
    Dish aggregation related runtime dependencies.
    """

    get_validation_results: Callable
    set_validation_results: Callable
    update_dish_vcc_flag: Callable
    reset_load_dish_cfg_data: Callable


@dataclass(slots=True)
class DeviceContext:
    """Device related runtime dependencies."""

    csp_mln_device_name: str

    dish_leaf_node_dev_names: list[str]

    get_dev: Callable[[str], Any]


@dataclass(slots=True, kw_only=True)
class LoadDishCfgCommandContext:
    """Generic command execution services."""

    # Command execution
    command_timeout: float

    # Command tracking
    update_command_in_progress_id: Callable[[str], None]

    set_load_dish_cfg_aggregated_result: Callable[[str], None]

    set_dish_vcc_command_status: Callable[[str, str], None]

    update_dish_vcc_flag: Callable[[str, bool], None]

    get_dish_vcc_validation_status: Callable[[str], bool]

    set_dish_vcc_validation_status: Callable[[str, bool], None]

    update_memorized_attribute: Callable

    # # Task / execution lifecycle
    # upd_abort_evt: Callable = None
    #
    # # Cleanup
    # clear_device_events: Callable = None


@dataclass(kw_only=True)
class LoadDishCfgRuntimeContext(CommandRuntimeContext):
    """
    Runtime dependencies required by the LoadDishCfg command.
    """

    device_ctx: DeviceContext
    command_ctx: LoadDishCfgCommandContext
    append_dish_dev_names: Callable[[list[str]], None]
    update_kval_aggregator: Callable[[str, Any], None]
    dish_kvalue_validation_aggregator: Any
    k_value_valid_range_lower_limit: int
    k_value_valid_range_upper_limit: int
    validate_dish_ids: Any

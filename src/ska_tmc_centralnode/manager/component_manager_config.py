"""Configuration for Central Node component managers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ska_control_model import OpStateModel
from ska_tmc_common.v4.ska_device_config import (
    TimeoutConfig,
    TmcComponentManagerConfig,
)


@dataclass(kw_only=True)
class GPMConfig:
    """Configuration to store GlobalPointingModel related data.

    Attributes:
        version: Default GPM version.
        interface: Default GPM interface.
        data_sources_prefix: Default GPM data sources prefix.
        file_path_prefix: Default GPM file path prefix.
        invoke_set_gpm_command_callback: Callable to invoke set GPM command.
    """

    version: str
    interface: str
    data_sources_prefix: str
    file_path_prefix: str
    invoke_command_callback: Callable


@dataclass(kw_only=True)
class DishVccConfig:
    """Configuration to store DishVccConfig related data.

    Attributes:
        uri: Default DishVccConfig URI.
        file_path: Default DishVccConfig file path.
        init_timeout: Default DishVccConfig command timeout during
        initialisation.
        enable_init: Flag to check whether invocation of DishVccCfg
        command during initialisation is enabled or not.
        invoke_command_callback: Callable to invoke DishVccCfg command.
        k_value_valid_range_upper_limit: Upper limit of the valid k-value
        range.
        k_value_valid_range_lower_limit: Lower limit of the valid k-value
        range.
        dish_k_value_aggregation_allowed_precent: Percentage of the dishes
        to be considered for DishKValue aggregation.
    """

    uri: str
    file_path: str
    init_timeout: float = 120
    enable_init: bool
    invoke_command_callback: Callable
    k_value_valid_range_upper_limit: int = 1177
    k_value_valid_range_lower_limit: int = 1
    dish_k_value_aggregation_allowed_precent: float = 100.0


@dataclass(kw_only=True)
class ArrayLayoutConfig:
    """Configuration to store ArrayLayoutConfig related data."""

    default_url: dict


@dataclass(kw_only=True)
class CentralNodeComponentManagerConfig(TmcComponentManagerConfig):
    """Configuration for Central Node component managers.

    Extends common node-level manager configuration with central node-specific
    inputs used by MID and LOW component manager.
    """

    op_state_model: OpStateModel
    array_layout_config: ArrayLayoutConfig
    timeout_config: TimeoutConfig
    subarray_trl_prefix: str
    retry_attempts: int = 5
    retry_delay: float = 3.0


@dataclass(kw_only=True)
class MidCentralNodeComponentManagerConfig(CentralNodeComponentManagerConfig):
    """Configuration for Central Node component managers for MID telescope.

    Extends common node-level manager configuration with central node-specific
    inputs used by MID component manager.
    """

    mkt_extension_id: str
    ska_dish_ranges: tuple[int, int] = (1, 999)
    mkt_dish_ranges: tuple[int, int] = (0, 63)
    dish_config: DishVccConfig
    gpm_config: GPMConfig


@dataclass(kw_only=True)
class LowCentralNodeComponentManagerConfig(CentralNodeComponentManagerConfig):
    """Configuration for Central Node component managers LOW telescope.

    Extends common node-level manager configuration with central node-specific
    inputs used by LOW component manager.
    """

    is_auto_recovery_enabled: bool

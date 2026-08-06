"""Common context dataclasses for CentralNode refactored commands."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class CommandInProgressContext:
    """Context to maintain command-in-progress data."""

    get_id: Callable
    update_id: Callable
    update_name: Callable
    clear: Callable
    get_name: Callable
    obj_update_cmd: Callable


@dataclass
class SbIDContext:
    """Context to maintain scheduler block ID."""

    set: Callable
    reset: Callable


@dataclass
class ObsStateContext:
    """Context to maintain observation state."""

    get: Callable
    change_callback: Callable


@dataclass
class AssignedResourcesAttributeContext:
    """Context to maintain assigned resources attribute."""

    set: Callable
    clear: Callable


@dataclass
class RecoveryContext:
    """Context for auto recovery handling."""

    update_progress: Callable
    is_enabled: bool
    check_time_duration: float
    set_device_list: Callable
    mccs_release_interface: str
    is_in_progress: Callable


@dataclass
class AbortedDishContext:
    """Context to manage aborted dishes."""

    get: Callable
    clear: Callable
    update: Callable


@dataclass
class ConfiguredDishLNContext:
    """Context to manage configured dish leaf nodes."""

    get: Callable
    remove: Callable

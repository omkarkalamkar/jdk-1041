"""Common context dataclasses for CentralNode refactored commands."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class CommandInProgressContext:
    """Context to maintain command-in-progress data."""

    update_name: Callable
    clear: Callable
    get_name: Callable


@dataclass
class ObsStateContext:
    """Context to maintain observation state."""

    get: Callable

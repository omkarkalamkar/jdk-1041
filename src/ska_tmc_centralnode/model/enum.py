"""Enum class for central node"""
from enum import IntEnum, unique


@unique
class ModesAvailability(IntEnum):
    """Avilable models enum class"""

    not_available = 0
    available = 1

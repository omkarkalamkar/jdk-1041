"""Enum class for central node"""

from enum import IntEnum, unique


@unique
class ModesAvailability(IntEnum):
    """Avilable models enum class"""

    NOT_AVAILABLE = 0
    AVAILABLE = 1


class DishConfigStatus(IntEnum):
    """Status for Dish Vcc Configuration"""

    STAGING = 0
    INIT = 1
    IN_PROGRESS = 2
    COMPLETED = 3
    FAILED = 4

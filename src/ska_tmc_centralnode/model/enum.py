from enum import IntEnum, unique


@unique
class ModesAvailability(IntEnum):
    not_available = 0
    available = 1

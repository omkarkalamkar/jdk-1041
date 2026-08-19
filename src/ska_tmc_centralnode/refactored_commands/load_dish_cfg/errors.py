"""
Custom exceptions for the load_dish_cfg command.
"""


class CommandInitializationError(Exception):
    """Raised when there is an error
    during command initialization.
    """


class DishAdapterError(Exception):
    """Raised when there is an error
    related to dish adapter operations.
    """


class SetKValueError(Exception):
    """Raised when there is an error
    while setting a key-value pair.
    """


class DishVccFetchError(Exception):
    """Raised when there is an error
    while fetching the dish VCC map.
    """

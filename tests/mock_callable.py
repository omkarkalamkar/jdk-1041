"""A module for mocking the task callback functionality"""

from typing import Callable

from ska_control_model import TaskStatus


class MockCallable(Callable):
    """A mock class for task callbacks"""

    def __init__(
        self,
        unique_id: str,
    ):
        """Initialise the callable with unique id"""
        self._unique_id = unique_id
        self.status: TaskStatus = None
        self.result: str = None
        self.exception: str = None

    def __call__(
        self,
        status: TaskStatus = None,
        result: str = None,
        exception: str = None,
    ) -> TaskStatus:
        """Call method to set the status, result and message"""
        self.status = status
        self.result = result
        self.exception = exception
        return self.status

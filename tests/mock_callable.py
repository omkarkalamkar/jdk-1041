"""A module for mocking the task callback functionality"""

from typing import Optional

from ska_control_model import TaskStatus


class MockCallable:
    """A mock class for task callbacks"""

    def __init__(
        self,
        unique_id: str,
    ):
        """Initialise the callable with unique id"""
        self._unique_id = unique_id
        self.status: Optional[TaskStatus] = None
        self.result: Optional[str] = None
        self.exception: Optional[str] = None

    def __call__(
        self,
        status: TaskStatus,
        result: Optional[str] = None,
        exception: Optional[str] = None,
    ) -> TaskStatus:
        """Call method to set the status, result and message"""
        self.status = status
        self.result = result
        self.exception = exception
        return self.status

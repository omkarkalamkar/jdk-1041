"""Module for exception decorator"""
import functools
import threading

from ska_control_model import ResultCode, TaskStatus
from ska_tango_base.faults import StateModelError
from ska_tango_base.type_hints import TaskCallbackType
from ska_tmc_common import CommandNotAllowed, SubarrayNotPresentError

from ..manager.component_manager import CNComponentManager


def exception_handler(command_name: str):
    """Adds the exception handling to the command definition."""

    def exception_decorator(func):
        @functools.wraps(func)
        def wrapper_function(
            self: CNComponentManager,
            argin: str,
            task_callback: TaskCallbackType,
            task_abort_event: threading.Event,
        ):
            try:
                func(self, argin, task_callback, task_abort_event)
            except (
                StateModelError,
                CommandNotAllowed,
                SubarrayNotPresentError,
            ) as exception:
                self.logger.exception(
                    "Exception occurred while processing " + "%s: %s ",
                    command_name,
                    exception,
                )
                task_callback(
                    status=TaskStatus.REJECTED,
                    result=(ResultCode.NOT_ALLOWED, str(exception)),
                )

            except Exception as exception:
                self.logger.exception(
                    "Exception occurred while processing " + "%s: %s ",
                    command_name,
                    exception,
                )
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode.FAILED, str(exception)),
                )

        return wrapper_function

    return exception_decorator

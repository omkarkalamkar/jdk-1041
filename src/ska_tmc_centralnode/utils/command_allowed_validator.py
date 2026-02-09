"""
Decorator module for validating command execution in Central Node.

This module provides decorators to validate command execution permissions
based on subarray observation state and device responsiveness.
"""

import functools
import json
from typing import Any, Callable, List

from ska_tmc_common.exceptions import InvalidJSONError


def check_command_allowed(
    desired_obsstate: List,
    command_name: str = "",
):
    """
    Decorator to validate if a command is allowed based on subarray state.
    This decorator extracts the subarray_id from the JSON argument
    and validates that the subarray is in one of the
    desired observation states.

    Args:
        desired_obsstate (List): List of allowed ObsState values.
        command_name (str): Name of the command for error messages.

    Returns:
        Callable: Decorated function.

    Raises:
        StateModelError: If subarray is not in allowed observation state.
        InvalidJSONError: If subarray_id is missing from JSON argument.

    Example:
        @validate_subarray_in_obsstate(
            desired_obsstate=[ObsState.EMPTY],
            command_name="AssignResources"
        )
        def assign_resources(self, argin):

    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            cmd_name = command_name or func.__name__

            # Extract subarray_id from JSON argument
            if args and isinstance(args[0], str):
                try:
                    json_arg = json.loads(args[0])
                    if isinstance(json_arg, dict):
                        subarray_id = json_arg.get("subarray_id")
                        if subarray_id is None:
                            raise InvalidJSONError(
                                "subarray_id key is not present in the "
                                "input json argument"
                            )

                        # Validate using component manager
                        if hasattr(self, "component_manager"):
                            self.component_manager.is_command_allowed_callable(
                                subarray_id=subarray_id,
                                command_name=cmd_name,
                            )
                except json.JSONDecodeError as e:
                    raise InvalidJSONError(
                        f"Problem in loading the JSON string: {e}"
                    ) from e
                except Exception as exception:
                    raise exception

            # Execute the actual command
            return func(self, *args, **kwargs)

        return wrapper

    return decorator

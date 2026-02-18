"""Module containing decorators for JSON validation.

This module provides decorators that validate JSON arguments for
assign and release commands, ensuring proper format and content
before execution.
"""
import functools
import json
import logging

from ska_tango_base.commands import ResultCode

from ska_tmc_centralnode.model.enum import DishConfigStatus


def assign_validate_json_args(meth):
    """Decorator to validate JSON arguments for assign commands.

    This decorator validates that the input is valid JSON and passes it through
    the assign validation method before executing the wrapped method.

    :param meth: The method to be decorated
    :type meth: callable
    :return: Wrapped method with JSON validation
    :rtype: callable
    """

    @functools.wraps(meth)
    def wrapper(self, json_str: str):
        logging.info("Validating JSON argument: %s", json_str)

        try:
            json.loads(json_str)
        except json.JSONDecodeError:
            return [ResultCode.REJECTED], ["Malformed input JSON"]

        validator = getattr(self, "component_manager", self)
        argin, exception_msg = validator.validate_assign_json(json_str)
        if exception_msg:
            self.logger.debug("Validation failed")
            return [ResultCode.REJECTED], [exception_msg]

        return meth(self, argin)

    return wrapper


def release_validate_json_args(meth):
    """Decorator to validate JSON arguments for release commands.

    This decorator validates that the input is valid JSON and passes it through
    the release validation method before executing the wrapped method.

    :param meth: The method to be decorated
    :type meth: callable
    :return: Wrapped method with JSON validation
    :rtype: callable
    """

    @functools.wraps(meth)
    def wrapper(self, json_str: str):
        logging.info("Validating JSON argument: %s", json_str)
        try:
            json.loads(json_str)
        except json.JSONDecodeError:
            return [ResultCode.REJECTED], ["Malformed input JSON"]

        validator = getattr(self, "component_manager", self)
        argin, exception_msg = validator.validate_release_json(json_str)
        if exception_msg:
            self.logger.debug("Validation failed")
            return [ResultCode.REJECTED], [exception_msg]

        return meth(self, argin)

    return wrapper


def validate_dish_vcc_command_status(meth):
    """Decorator to validate dish VCC command status for load_dish_cfg.

    This decorator checks if a dish VCC configuration command is already
    in progress and rejects the new command before execution if needed.

    :param meth: The method to be decorated
    :type meth: callable
    :return: Wrapped method with status validation
    :rtype: callable
    """

    @functools.wraps(meth)
    def wrapper(self, json_str: str):
        logging.info("Validating dish VCC command status")

        component_manager = getattr(self, "component_manager", self)

        if component_manager.dish_vcc_command_status in (
            DishConfigStatus.STAGING,
            DishConfigStatus.IN_PROGRESS,
        ):
            dish_config_status_name = DishConfigStatus(
                component_manager.dish_vcc_command_status
            ).name
            message = (
                "Dish Vcc Configuration is in Progress. "
                f"Dish Vcc command status: {dish_config_status_name}"
            )
            logging.debug(message)
            return [ResultCode.REJECTED], [message]

        return meth(self, json_str)

    return wrapper

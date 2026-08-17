"""
Contains the runtime context classes for the SetGlobalPointingModel command.
"""

import json
import logging
from dataclasses import dataclass
from json import JSONDecodeError
from threading import Lock
from typing import Any, Callable

from ska_tmc_common.v4.command_context import CommandRuntimeContext


class GPMPrepError(Exception):
    """Raised when Global Pointing model request preparation fails."""


@dataclass
class CommandInProgressContext:
    """Context to maintain command in progress data.

    Attributes:
        get_id: Callable to fetch current command in progress id.
        update_id: Callable to update current command in progress id.
        update_name: Callable to update current command in progress name.
        clear: Callable to clear the command object from
        in progress object list.
        get_name: Callable to get command in progress.
        obj_update_cmd: Callable to update command in progress
        object with current command.
    """

    get_id: Callable
    update_id: Callable
    update_name: Callable
    clear: Callable
    get_name: Callable
    obj_update_cmd: Callable


@dataclass(kw_only=True)
class GPMContext(CommandRuntimeContext):
    """GPM context containing runtime parameters for the Mid telescope
    Subarray."""

    command_timeout: float
    cmd_inprogress_ctx: CommandInProgressContext
    gpm_unknown_dishes: list
    dishln_gpm_cmd_exe_data: dict
    is_already_assigned: Callable
    update_abort_evt: Callable
    get_dish_leaf_node_device_names: Callable
    get_default_gpm_version_params: Callable
    get_device: Callable
    dish_leaf_node_prefix: str
    get_evt_data_manager: Callable
    dishln_gpm_lock: Lock
    global_pointing_model_status: dict
    reset_gpm_data: Callable

    def make_strategy(self, logger: logging.Logger) -> "GPMStrategy":
        """Create a global pointing model strategy.

        Args:
            logger: Logger instance for strategy operations.

        Returns:
            GPMStrategy: Global pointing model strategy.
        """

        return GPMStrategy(
            logger,
            self.gpm_unknown_dishes,
            self.get_default_gpm_version_params,
        )


@dataclass
class GPMPlan:
    """Data carrier for Scan command execution parameters."""

    apm_payload: dict


class GPMRequestError(ValueError):
    """Raised when JSON parsing of GPM request fails."""


class GPMRequest:
    """Parsed global pointing model request from JSON input."""

    def __init__(self, data: dict) -> None:
        self.data = data

    @classmethod
    def from_json(cls, argin: str) -> "GPMRequest":
        """Parse JSON input into a Global pointing model request."""
        try:
            return json.loads(argin)
        except JSONDecodeError as json_error:
            raise GPMRequestError(
                f"JSON parsing failed with exception: {json_error}"
            ) from json_error


class GPMStrategy:
    """Global pointing model strategy for SKA Mid telescope deployment."""

    def __init__(
        self,
        logger,
        gpm_unknown_dishes,
        get_default_gpm_version_params,
    ) -> None:
        """Initialize the Global Pointing Model strategy.

        :param logger: Logger used for command logging.
        :param gpm_unknown_dishes: Collection of unknown GPM dishes.
        :param get_default_gpm_version_params: Callback to get default
            GPM version parameters.
        """

        self.logger = logger
        self.gpm_unknown_dishes = gpm_unknown_dishes
        self.get_default_gpm_version_params = get_default_gpm_version_params

    def build_plan(self, request: Any, gpm_files=None) -> GPMPlan:
        """Build the Global Pointing Model plan from the request.

        :param request: GPM request containing the required parameters.
        :type request: Any
        :param gpm_files: Optional list of GPM files to include in the plan.
        :type gpm_files: list | None
        :return: Generated GPM plan.
        :rtype: GPMPlan
        """
        try:
            if gpm_files:
                payload, gpm_files = self.form_gpm_file_for_each_dish(
                    gpm_files, request
                )
            else:
                payload, gpm_files = self.form_gpm_path_from_receptors(request)
            return GPMPlan(apm_payload=payload), gpm_files
        except Exception as exception:
            raise GPMPrepError(
                "Exception occurred while building GPM plan " f"{exception}"
            ) from exception

    def form_gpm_file_for_each_dish(
        self, gpm_files: list, dish_gpm_params: dict
    ) -> tuple[dict, dict]:
        """Form GPM data for each dish from the available GPM files.

        :param gpm_files: List of GPM files from the data repository.
        :type gpm_files: list
        :param dish_gpm_params: GPM parameters for each dish.
        :type dish_gpm_params: dict
        :return: GPM data and dishes for which no GPM files were found.
        :rtype: tuple[dict, dict]
        """
        gpm_data = {}
        no_gpm_files_found = {}
        try:
            tm_data_source = dish_gpm_params.get("tm_data_sources", None)[0]
            tm_data_fpath = dish_gpm_params.get("tm_data_filepath", None)
            version = dish_gpm_params.get("version", None)
            self.logger.debug(
                "GPM Files found on data repository: %s", gpm_files
            )
            file_names = []
            while self.gpm_unknown_dishes:
                dish_id = self.gpm_unknown_dishes.pop()
                dish_id = dish_id.lower()
                file_names = [f for f in gpm_files if dish_id in f.lower()]
                if not file_names:
                    self.logger.debug(
                        "GPM file not found for dish %s", dish_id
                    )
                    error_message = (
                        "No GPM files were found for any of"
                        + " the bands in the provided paths"
                    )
                    no_gpm_files_found[dish_id] = error_message
                for file_name in file_names:
                    tm_data_sources = (
                        tm_data_source + "?" + version + "#tmdata"
                    )
                    tm_data_filepath = tm_data_fpath + "/" + file_name
                    if dish_id not in gpm_data:
                        gpm_data[dish_id] = []
                    gpm_data[dish_id].append(
                        {
                            "tm_data_sources": tm_data_sources,
                            "tm_data_filepath": tm_data_filepath,
                        }
                    )
        except Exception:
            self.logger.exception(
                "Exception occurred while forming GPM files."
            )
        return gpm_data, no_gpm_files_found

    def form_gpm_path_from_receptors(self, argin: dict) -> tuple[dict, dict]:
        """Form inputs for the ApplyPointingModel command.

        :param argin: Dictionary containing manual command input
            provided by the operator.
        :type argin: dict
        :return: Dictionary containing the GPM paths.
        :rtype: dict
        """
        gpm_data = {}
        default_params = self.get_default_gpm_version_params()
        tm_data_sources = default_params.get("tm_data_sources", None)[0]
        tm_data_sources = (
            tm_data_sources + "?" + argin.get("version", None) + "#tmdata"
        )
        receptors = argin["receptors"].items()

        for dish_id, bands in receptors:
            dish_id = dish_id.lower()
            for band in bands:
                file_name = f"gpm-{dish_id.lower()}-{band}.json"
                if dish_id not in gpm_data:
                    gpm_data[dish_id] = []
                tm_data_filepath = (
                    default_params.get("tm_data_filepath", None)
                    + "/"
                    + file_name
                )
                gpm_data[dish_id].append(
                    {
                        "tm_data_sources": tm_data_sources,
                        "tm_data_filepath": tm_data_filepath,
                    }
                )
        return gpm_data, {}

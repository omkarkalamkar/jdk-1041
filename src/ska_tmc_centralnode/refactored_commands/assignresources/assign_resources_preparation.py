"""Shared preparation helpers for CentralNode AssignResources."""

from __future__ import annotations

import logging

from ska_tmc_centralnode.model.input import InputParameterMid

from .assign_resources_request import (
    AssignResourcesRequest,
    AssignResourcesRequestError,
)


class AssignResourcesPreparationError(Exception):
    """Raised when AssignResources preparation fails."""


class AssignResourcesPreparation:
    """Request parsing and array layout handling for AssignResources."""

    def __init__(self, component_manager, logger: logging.Logger) -> None:
        self.component_manager = component_manager
        self.logger = logger

    def prepare_request(
        self,
        argin: str,
        *,
        remove_transaction_id: bool = False,
    ) -> AssignResourcesRequest:
        """Parse request and apply array layout/default behavior."""
        try:
            request = AssignResourcesRequest.from_json(argin)
        except AssignResourcesRequestError as exception:
            raise AssignResourcesPreparationError(
                f"Problem in loading the JSON string: {exception}"
            ) from exception

        request_data = request.copy_data()

        if remove_transaction_id and "transaction_id" in request_data:
            del request_data["transaction_id"]

        self._apply_array_layout(request_data)
        return AssignResourcesRequest(request_data)

    def _apply_array_layout(self, request_data: dict) -> None:
        if "telmodel" in request_data:
            array_url = request_data["telmodel"]
            self._validate_array_layout(array_url, key_name="telmodel")
            self.component_manager.array_layout_url = array_url
            self.logger.debug("array_layout_url in argin: %s", array_url)
            return

        default_url = getattr(
            self.component_manager,
            "default_array_layout_url",
            "",
        )
        if not default_url:
            self.logger.debug(
                "No array_layout_url in argin and no "
                "default_array_layout_url set"
            )
            return

        if not isinstance(default_url, dict):
            if isinstance(
                self.component_manager.input_parameter,
                InputParameterMid,
            ):
                message = (
                    "Invalid default 'telmodel': expected a " + "dictionary."
                )
            else:
                message = (
                    "Invalid default ArrayLayout : expected a " + "dictionary."
                )
            raise AssignResourcesPreparationError(message)

        self._validate_array_layout(
            default_url,
            key_name="default_array_layout_url",
        )

        request_data["telmodel"] = default_url
        self.component_manager.array_layout_url = default_url
        self.logger.debug(
            "array_layout_url not provided, using default: %s",
            default_url,
        )

    def _validate_array_layout(
        self,
        array_url: dict,
        *,
        key_name: str,
    ) -> None:
        """Validate array layout payload required by AssignResources."""
        if not isinstance(array_url, dict):
            raise AssignResourcesPreparationError(
                f"Invalid '{key_name}': expected a dictionary."
            )

        if "array_layout_path" not in array_url:
            raise AssignResourcesPreparationError(
                f"Invalid '{key_name}': missing 'array_layout_path'."
            )
        if not array_url["array_layout_path"]:
            raise AssignResourcesPreparationError(
                f"Invalid '{key_name}': empty 'array_layout_path'."
            )

        if "source_uris" not in array_url:
            raise AssignResourcesPreparationError(
                f"Invalid '{key_name}': missing 'source_uris'."
            )

        source_uris = array_url["source_uris"]
        if not isinstance(source_uris, list):
            raise AssignResourcesPreparationError(
                f"Invalid '{key_name}': 'source_uris' must be a list."
            )
        if not source_uris:
            raise AssignResourcesPreparationError(
                f"Invalid '{key_name}': empty 'source_uris'."
            )
        if source_uris == [""]:
            raise AssignResourcesPreparationError(
                f"Invalid '{key_name}': empty URI in 'source_uris'."
            )

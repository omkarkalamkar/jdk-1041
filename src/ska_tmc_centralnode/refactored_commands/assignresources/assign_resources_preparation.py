"""Shared preparation helpers for CentralNode AssignResources."""

from __future__ import annotations

import logging

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
            raise AssignResourcesPreparationError(
                "Invalid default 'telmodel': expected a dictionary."
            )

        request_data["telmodel"] = default_url
        self.component_manager.array_layout_url = default_url
        self.logger.debug(
            "array_layout_url not provided, using default: %s",
            default_url,
        )

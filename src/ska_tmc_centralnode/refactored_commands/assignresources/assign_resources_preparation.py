"""Shared preparation helpers for CentralNode AssignResources."""

from __future__ import annotations

import logging

from ska_tmc_centralnode.model.input import InputParameterMid

from .assign_resources_context import AssignResourcesContext
from .assign_resources_request import (
    AssignResourcesRequest,
    AssignResourcesRequestError,
)


class AssignResourcesPreparationError(Exception):
    """Raised when AssignResources JSON input fails to parse."""


class InvalidArrayLayoutError(Exception):
    """Raised when default array layout is not a dict. Message is final
    and must not be re-wrapped by callers."""


class AssignResourcesPreparation:
    """Request parsing and array layout handling for AssignResources."""

    def __init__(
        self,
        command_runtime_context: AssignResourcesContext,
        logger: logging.Logger,
    ) -> None:
        self.command_runtime_context = command_runtime_context
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
        """Apply array layout from request or default if not provided.
        If the request contains a 'telmodel' field, it is used to update the
        array layout context. If not, the default array layout is fetched from
        the context and used to update the array layout context. If neither is
        available, no action is taken. If the default array layout is not a
        dictionary, an InvalidArrayLayoutError is raised.
        """
        if "telmodel" in request_data:
            array_url = request_data["telmodel"]
            self.command_runtime_context.array_layout_ctx.update_url(array_url)
            self.logger.debug("array_layout_url in argin: %s", array_url)
            return

        try:
            default_url = (
                self.command_runtime_context.array_layout_ctx.get_default_url()
            )
        except AttributeError:
            default_url = ""
        if not default_url:
            self.logger.debug(
                "No array_layout_url in argin and no "
                "default_array_layout_url set"
            )
            return

        if not isinstance(default_url, dict):
            if isinstance(
                self.command_runtime_context.input_parameter,
                InputParameterMid,
            ):
                message = "Invalid default 'telmodel': expected a dictionary."
            else:
                message = (
                    "Invalid default ArrayLayout : expected a dictionary."
                )
            raise InvalidArrayLayoutError(message)

        request_data["telmodel"] = default_url
        self.command_runtime_context.array_layout_ctx.update_url(default_url)
        self.logger.debug(
            "array_layout_url not provided, using default: %s",
            default_url,
        )

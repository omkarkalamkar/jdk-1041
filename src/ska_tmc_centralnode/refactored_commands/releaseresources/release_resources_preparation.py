"""Shared preparation helpers for CentralNode ReleaseResources."""

import logging

from .release_resources_context import ReleaseResourcesContext
from .release_resources_request import (
    ReleaseResourcesRequest,
    ReleaseResourcesRequestError,
)


class ReleaseResourcesPreparationError(Exception):
    """Raised when ReleaseResources preparation fails."""


class ReleaseResourcesPreparation:
    """Request parsing helper for ReleaseResources."""

    def __init__(
        self,
        command_runtime_context: ReleaseResourcesContext,
        logger: logging.Logger,
    ) -> None:
        self.command_runtime_context: ReleaseResourcesContext = (
            command_runtime_context
        )
        self.logger = logger

    def prepare_request(
        self,
        argin: str,
        *,
        remove_transaction_id: bool = True,
    ) -> ReleaseResourcesRequest:
        """Parse request and normalize optional fields."""
        try:
            request = ReleaseResourcesRequest.from_json(argin)
        except ReleaseResourcesRequestError as exception:
            raise ReleaseResourcesPreparationError(
                f"Problem in loading the JSON string: {exception}"
            ) from exception

        request_data = request.copy_data()
        if remove_transaction_id and "transaction_id" in request_data:
            del request_data["transaction_id"]

        return ReleaseResourcesRequest(request_data)

"""Shared preparation helpers for CentralNode ReleaseResources."""

from .release_resources_request import (
    ReleaseResourcesRequest,
    ReleaseResourcesRequestError,
)


class ReleaseResourcesPreparationError(Exception):
    """Raised when ReleaseResources preparation fails."""


class ReleaseResourcesPreparation:
    """Request parsing helper for ReleaseResources."""

    def __init__(self, component_manager, logger) -> None:
        self.component_manager = component_manager
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

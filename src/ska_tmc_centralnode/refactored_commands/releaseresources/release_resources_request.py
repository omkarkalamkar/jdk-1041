"""Parsing and representation of CentralNode ReleaseResources requests."""

import copy
import json
from json import JSONDecodeError


class ReleaseResourcesRequestError(ValueError):
    """Raised when JSON parsing of ReleaseResources request fails."""


class ReleaseResourcesRequest:
    """Parsed ReleaseResources request from JSON input."""

    def __init__(self, data: dict) -> None:
        self.data = data

    @classmethod
    def from_json(cls, argin: str) -> "ReleaseResourcesRequest":
        """Parse the input JSON string into a ReleaseResourcesRequest."""
        try:
            return cls(json.loads(argin))
        except JSONDecodeError as json_error:
            raise ReleaseResourcesRequestError(
                f"JSON parsing failed with exception: {json_error}"
            ) from json_error

    @property
    def subarray_id(self) -> int:
        """Return the target subarray ID as integer."""
        return int(self.data["subarray_id"])

    @property
    def release_all(self) -> bool:
        """Return whether full release is requested."""
        return bool(self.data["release_all"])

    def copy_data(self) -> dict:
        """Return a deep copy of the underlying request data."""
        return copy.deepcopy(self.data)

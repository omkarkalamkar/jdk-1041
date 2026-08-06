"""Parsing and representation of CentralNode AssignResources requests."""

import copy
import json
from json import JSONDecodeError


class AssignResourcesRequestError(ValueError):
    """Raised when JSON parsing of AssignResources request fails."""


class AssignResourcesRequest:
    """Parsed AssignResources request from JSON input."""

    def __init__(self, data: dict) -> None:
        self.data = data

    @classmethod
    def from_json(cls, argin: str) -> "AssignResourcesRequest":
        """Parse the input JSON string into an AssignResourcesRequest."""
        try:
            return cls(json.loads(argin))
        except JSONDecodeError as json_error:
            raise AssignResourcesRequestError(
                f"JSON parsing failed with exception: {json_error}"
            ) from json_error

    @property
    def csp(self) -> dict:
        return self.data.get("csp", {})

    @property
    def sdp(self) -> dict:
        return self.data.get("sdp", {})

    @property
    def mccs(self) -> dict:
        return self.data.get("mccs", {})

    @property
    def receptor_ids(self) -> list:
        return self.data["dish"]["receptor_ids"]

    @property
    def subarray_id(self) -> int:
        return int(self.data["subarray_id"])

    @property
    def execution_block(self) -> dict:
        return self.sdp.get("execution_block", {})

    def copy_data(self) -> dict:
        return copy.deepcopy(self.data)

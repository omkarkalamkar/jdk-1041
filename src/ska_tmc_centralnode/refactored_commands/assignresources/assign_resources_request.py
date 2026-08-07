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
        """Return the CSP section from the request payload."""
        return self.data.get("csp", {})

    @property
    def sdp(self) -> dict:
        """Return the SDP section from the request payload."""
        return self.data.get("sdp", {})

    @property
    def mccs(self) -> dict:
        """Return the MCCS section from the request payload."""
        return self.data.get("mccs", {})

    @property
    def receptor_ids(self) -> list:
        """Return receptor IDs requested in the dish section."""
        return self.data["dish"]["receptor_ids"]

    @property
    def subarray_id(self) -> int:
        """Return the target subarray ID as integer."""
        return int(self.data["subarray_id"])

    @property
    def execution_block(self) -> dict:
        """Return execution_block from SDP payload when available."""
        return self.sdp.get("execution_block", {})

    def copy_data(self) -> dict:
        """Return a deep copy of the underlying request data."""
        return copy.deepcopy(self.data)

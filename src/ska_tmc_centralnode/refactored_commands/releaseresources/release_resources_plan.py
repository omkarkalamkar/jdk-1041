"""Data classes used by CentralNode ReleaseResources refactor."""

from dataclasses import dataclass


@dataclass
class ReleaseResourcesPlan:
    """Data carrier for ReleaseResources command execution parameters."""

    payload: dict
    subarray_id: int
    release_all: bool


@dataclass
class MidReleaseResourcesPlan(ReleaseResourcesPlan):
    """Data carrier for MID specific ReleaseResources parameters."""


@dataclass
class LowReleaseResourcesPlan(ReleaseResourcesPlan):
    """Data carrier for LOW specific ReleaseResources parameters."""

    mccs_payload: str

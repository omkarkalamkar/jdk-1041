"""Data classes used by CentralNode AssignResources refactor."""

from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class AssignResourcesPlan:
    """Data carrier for AssignResources command execution parameters."""

    csp_payload: str
    sdp_payload: str
    sb_id: str
    telmodel: Dict
    subarray_id: int


@dataclass
class MidAssignResourcesPlan(AssignResourcesPlan):
    """Data carrier for MID specific AssignResources parameters."""

    scan_type_id: str
    visibilities_beam_id: str
    receptor_ids: List


@dataclass
class LowAssignResourcesPlan(AssignResourcesPlan):
    """Data carrier for LOW specific AssignResources parameters."""

    mccs_payload: str
    subsystems: Set[str]

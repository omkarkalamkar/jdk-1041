"""Data classes used by CentralNode AssignResources refactor."""

from dataclasses import dataclass


@dataclass
class AssignResourcesPlan:
    """Data carrier for AssignResources command execution parameters.

    Attributes:
        payload: Fully assembled, ready-to-send JSON payload for the
            AssignResources call on the TM Subarray device.
        sb_id: SB ID from execution block of SDP assign resources.
        telmodel: Telmodel resources present in assign resources.
        subarray_id: Subarray id present in assign resources.
    """

    payload: str
    sb_id: str
    telmodel: dict
    subarray_id: int


@dataclass
class MidAssignResourcesPlan(AssignResourcesPlan):
    """Data carrier for MID specific AssignResources parameters."""

    scan_type_id: str
    visibilities_beam_id: str
    receptor_ids: list


@dataclass
class LowAssignResourcesPlan(AssignResourcesPlan):
    """Data carrier for LOW specific AssignResources parameters.

    Attributes:
        mccs_payload: Ready-to-send JSON payload for the AssignResources
            call on the MCCS Master Leaf Node.
        subsystems: Subsystems present in assign resources.
    """

    mccs_payload: str
    subsystems: set[str]

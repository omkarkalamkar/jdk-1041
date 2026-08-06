"""AssignResources strategy implementations for CentralNode."""

import json
import logging
from abc import ABC, abstractmethod

from ska_tmc_centralnode.utils.constants import SUB_SYSTEMS

from .assign_resources_plan import (
    AssignResourcesPlan,
    LowAssignResourcesPlan,
    MidAssignResourcesPlan,
)
from .assign_resources_request import AssignResourcesRequest


class AssignResourcesPrepError(Exception):
    """Raised when AssignResources request preparation fails."""


class AssignResourcesStrategy(ABC):
    """Abstract base class for telescope-specific AssignResources behavior."""

    def __init__(
        self, logger: logging.Logger, csp_interface: str = ""
    ) -> None:
        self.logger = logger
        self.csp_interface = csp_interface

    @abstractmethod
    def build_plan(
        self, request: AssignResourcesRequest
    ) -> AssignResourcesPlan:
        """Build a typed execution plan from a parsed request."""


class MidAssignResourcesStrategy(AssignResourcesStrategy):
    """AssignResources strategy for SKA Mid deployment."""

    def build_plan(
        self, request: AssignResourcesRequest
    ) -> MidAssignResourcesPlan:
        try:
            sb_id, scan_id, vis_bm_id = "", "", ""
            csp_payload = request.copy_data().get("csp", {})
            if self.csp_interface:
                csp_payload["interface"] = self.csp_interface

            if request.execution_block:
                sb_id = request.execution_block["eb_id"]
                scan_id, vis_bm_id = self._get_scan_vis_bm(
                    request.execution_block
                )

            telmodel: dict = request.data.get("telmodel", {})
            receptor_ids: list = request.receptor_ids
            subarray_id: int = request.subarray_id
        except KeyError as key_error:
            raise AssignResourcesPrepError(
                "AssignResources json necessary key missing: "
                f"{key_error.args[0]}"
            ) from key_error
        except Exception as exception:
            raise AssignResourcesPrepError(
                "Exception occurred while building assign json plan "
                f"{exception}"
            ) from exception

        return MidAssignResourcesPlan(
            csp_payload=json.dumps(csp_payload),
            sdp_payload=json.dumps(request.sdp),
            sb_id=sb_id,
            scan_type_id=scan_id,
            visibilities_beam_id=vis_bm_id,
            telmodel=telmodel,
            subarray_id=subarray_id,
            receptor_ids=receptor_ids,
        )

    def _get_scan_vis_bm(self, execution_block: dict) -> tuple:
        try:
            visibility_beam_id = None
            scan_type_id = None
            for beams in execution_block.get("beams", {}):
                if beams.get("function") == "visibilities":
                    visibility_beam_id = beams.get("beam_id")
                    break

            for scan_type in execution_block.get("scan_types", {}):
                if visibility_beam_id in scan_type.get("beams"):
                    temp_scan_type_id = scan_type.get("scan_type_id")
                    if temp_scan_type_id and not temp_scan_type_id.startswith(
                        "."
                    ):
                        scan_type_id = temp_scan_type_id
                        break
            return scan_type_id, visibility_beam_id
        except Exception as exception:
            message = (
                "Error while extracting scan type or visibilities beam id"
            )
            self.logger.exception("%s: %s", message, exception)
            raise AssignResourcesPrepError(message) from exception


class LowAssignResourcesStrategy(AssignResourcesStrategy):
    """AssignResources strategy for SKA Low deployment."""

    def build_plan(
        self, request: AssignResourcesRequest
    ) -> LowAssignResourcesPlan:
        try:
            sb_id: str = ""
            csp_resources: dict = request.copy_data().get("csp", {})
            if self.csp_interface:
                csp_resources["interface"] = self.csp_interface
            csp_resources.setdefault("common", {})
            csp_resources["common"]["subarray_id"] = request.subarray_id
            csp_resources.setdefault("lowcbf", {})

            mccs_resources = request.copy_data().get("mccs", {})
            mccs_resources["subarray_id"] = request.subarray_id

            sdp_resources = request.sdp
            if request.execution_block:
                sb_id = request.execution_block["eb_id"]

            telmodel: dict = request.data.get("telmodel", {})
            subsystems: set[str] = SUB_SYSTEMS.intersection(
                request.data.keys()
            )
        except KeyError as key_error:
            raise AssignResourcesPrepError(
                "AssignResources json necessary key missing: "
                f"{key_error.args[0]}"
            ) from key_error
        except Exception as exception:
            raise AssignResourcesPrepError(
                "Exception occurred while building assign json plan "
                f"{exception}"
            ) from exception

        return LowAssignResourcesPlan(
            csp_payload=json.dumps(csp_resources),
            sdp_payload=json.dumps(sdp_resources),
            mccs_payload=json.dumps(mccs_resources),
            sb_id=sb_id,
            telmodel=telmodel,
            subarray_id=request.subarray_id,
            subsystems=subsystems,
        )

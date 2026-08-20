"""ReleaseResources strategy implementations for CentralNode."""

import json
import logging
from abc import ABC, abstractmethod

from ska_tmc_centralnode.utils.constants import mccs_release_interface

from .release_resources_plan import (
    LowReleaseResourcesPlan,
    MidReleaseResourcesPlan,
    ReleaseResourcesPlan,
)
from .release_resources_request import ReleaseResourcesRequest


class ReleaseResourcesPrepError(Exception):
    """Raised when ReleaseResources request preparation fails."""


class ReleaseResourcesStrategy(ABC):
    """Abstract base class for telescope-specific ReleaseResources behavior."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    @abstractmethod
    def build_plan(
        self, request: ReleaseResourcesRequest
    ) -> ReleaseResourcesPlan:
        """Build a typed execution plan from a parsed request."""


class MidReleaseResourcesStrategy(ReleaseResourcesStrategy):
    """ReleaseResources strategy for SKA Mid deployment."""

    def build_plan(
        self, request: ReleaseResourcesRequest
    ) -> MidReleaseResourcesPlan:
        """Build a typed, fully-serialized execution plan from a parsed request
        :param request: Parsed ReleaseResourcesRequest object.
        :type request: ReleaseResourcesRequest
        :return: MidReleaseResourcesPlan object containing the execution plan.
        :rtype: MidReleaseResourcesPlan
        :raises ReleaseResourcesPrepError: If required keys are missing or
            an exception occurs during plan building."""
        try:
            payload = request.copy_data()
            subarray_id = request.subarray_id
            release_all = request.release_all
        except KeyError as key_error:
            raise ReleaseResourcesPrepError(
                "ReleaseResources json necessary key missing: "
                f"{key_error.args[0]}"
            ) from key_error
        except Exception as exception:
            raise ReleaseResourcesPrepError(
                "Exception occurred while building release json plan "
                f"{exception}"
            ) from exception

        return MidReleaseResourcesPlan(
            payload=payload,
            subarray_id=subarray_id,
            release_all=release_all,
        )


class LowReleaseResourcesStrategy(ReleaseResourcesStrategy):
    """ReleaseResources strategy for SKA Low deployment."""

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__(logger)
        self.mccs_interface = mccs_release_interface

    def build_plan(
        self, request: ReleaseResourcesRequest
    ) -> LowReleaseResourcesPlan:
        """Build a typed, fully-serialized execution plan
        from a parsed request.
        :param request: Parsed ReleaseResourcesRequest object.
        :type request: ReleaseResourcesRequest
        :return: LowReleaseResourcesPlan object containing the execution plan.
        :rtype: LowReleaseResourcesPlan
        :raises ReleaseResourcesPrepError: If required keys are missing or
            an exception occurs during plan building."""
        try:
            payload = request.copy_data()
            subarray_id = request.subarray_id
            release_all = request.release_all

            mccs_payload = request.copy_data()
            mccs_payload["interface"] = self.mccs_interface
        except KeyError as key_error:
            raise ReleaseResourcesPrepError(
                "ReleaseResources json necessary key missing: "
                f"{key_error.args[0]}"
            ) from key_error
        except Exception as exception:
            raise ReleaseResourcesPrepError(
                "Exception occurred while building release json plan "
                f"{exception}"
            ) from exception

        return LowReleaseResourcesPlan(
            payload=json.dumps(payload),
            subarray_id=subarray_id,
            release_all=release_all,
            mccs_payload=json.dumps(mccs_payload),
        )

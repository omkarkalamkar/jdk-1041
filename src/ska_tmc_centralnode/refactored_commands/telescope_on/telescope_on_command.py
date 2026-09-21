"""Base TelescopeOn command for CentralNode (shared Mid/Low behaviour)."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, cast

from ska_control_model import ResultCode, TaskStatus
from ska_tmc_common import AdapterFactory
from ska_tmc_common.adapters import AdapterType
from ska_tmc_common.v4.command_context import DeviceCommand
from tango import DevState

from ..common.base_command import BaseCNCommand
from .telescope_on_context import TelescopeOnContext
from .telescope_on_plan import TelescopeOnPlan


class BaseTelescopeOnCN(BaseCNCommand):
    """Shared TelescopeOn behaviour for CentralNode."""

    command_name = "TelescopeOn"

    def __init__(
        self,
        command_runtime_context: TelescopeOnContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
    ) -> None:
        super().__init__(command_runtime_context, adapter_provider, logger)
        self._plan: Optional[TelescopeOnPlan] = None
        self.unavailable_devices: List[str] = []

    def pre_process(self, argin=None) -> None:
        """Mark command in progress and set desired telescope state."""
        self.command_runtime_context.cmd_inprogress_ctx.update_name(
            self.__class__.__name__
        )
        self.command_runtime_context.desired_telescope_state = DevState.ON
        self.logger.debug(
            "Command ID: %s | Executing TelescopeOn",
            self.context.command_id,
        )

    def prepare_command(self) -> None:
        """No JSON input; prepare abort event, log state and build plan."""
        self.command_runtime_context.update_abort_evt(
            self.context.task_abort_event
        )
        self.command_runtime_context.log_state(
            "Device states before executing TelescopeOn command"
        )

        strategy = self.command_runtime_context.make_strategy(self.logger)
        self._plan = strategy.build_plan(self.command_runtime_context)
        self.unavailable_devices = list(self._plan.unavailable_devices)

    def is_state_complete(self) -> bool:
        """TelescopeOn completion check.

        Override in subclasses if a more precise check against
        telescopeState / aggregators is required.
        """
        # Default: rely on event-driven completion from BaseTMCCommand.
        # Adjust according to your aggregator logic if needed.
        return True

    def update_task_status(self, **kwargs) -> None:
        """Update LRC status; preserve unavailable-device messaging."""
        result = cast(Optional[Tuple[ResultCode, str]], kwargs.get("result"))
        status = kwargs.get("status", TaskStatus.COMPLETED)
        exception = kwargs.get("exception", "")

        if status == TaskStatus.ABORTED:
            self.context.task_callback(
                result=(ResultCode.ABORTED, "Command has been aborted"),
                status=status,
            )
            return

        if result is None:
            self.context.task_callback(
                result=(ResultCode.FAILED, exception or "Unknown error"),
                status=status,
                exception=exception,
            )
            return

        if result[0] == ResultCode.OK:
            msg = result[1] or "Command Completed"
            if self.unavailable_devices:
                msg = f"Unavailable devices are {self.unavailable_devices}"
            self.context.task_callback(
                result=(ResultCode.OK, msg), status=status
            )
        else:
            self.context.task_callback(
                result=(ResultCode.FAILED, result[1]),
                status=status,
                exception=exception or result[1],
            )

    # ------------------------------------------------------------------
    # Helpers used by Mid / Low subclasses
    # ------------------------------------------------------------------
    def _build_on_command(
        self, device_name: str, adapter_type: AdapterType
    ) -> DeviceCommand:
        return DeviceCommand(
            device_name=device_name,
            command_name="On",
            adapter_type=adapter_type,
        )

    def _build_set_standby_fp_command(self, device_name: str) -> DeviceCommand:
        return DeviceCommand(
            device_name=device_name,
            command_name="SetStandbyFPMode",
            adapter_type=AdapterType.DISH,
        )

    def _resolve_adapter_type(self, device_name: str) -> AdapterType:
        """Best-effort mapping from device name to AdapterType."""
        name_lower = device_name.lower()
        if "csp" in name_lower:
            return AdapterType.CSP_MASTER_LEAF_NODE
        if "sdp" in name_lower:
            return AdapterType.SDP_MASTER_LEAF_NODE
        if "mccs" in name_lower:
            return AdapterType.MCCS_MASTER_LEAF_NODE
        if "subarray" in name_lower:
            return AdapterType.SUBARRAY
        if "dish" in name_lower or "/d" in name_lower:
            return AdapterType.DISH
        # Fallback – adjust if your naming convention differs
        return AdapterType.SUBARRAY

    def are_all_results_received(self) -> bool:
        """TelescopeOn does not wait for longRunningCommandResult events.

        Matches the original implementation that reported completion
        immediately after the On / SetStandbyFPMode commands were sent.
        """
        return True

    def allowed_result_codes(self) -> set[ResultCode]:
        # Original code treated REJECTED (unavailable devices) as non-fatal
        return {ResultCode.OK, ResultCode.REJECTED}

    def evaluate_result(self) -> tuple[ResultCode, str]:
        if self.unavailable_devices:
            return (
                ResultCode.OK,
                f"Unavailable devices are {self.unavailable_devices}",
            )
        return super().evaluate_result()

"""TelescopeOffMid – Mid-specific TelescopeOff command."""

from __future__ import annotations

import logging

from ska_control_model import ResultCode
from ska_tmc_common import AdapterFactory
from ska_tmc_common.adapters import AdapterType

from .telescope_off_command import BaseTelescopeOffCN
from .telescope_off_context import MidTelescopeOffContext
from .telescope_off_executor import TelescopeOffExecutor


class TelescopeOffMid(BaseTelescopeOffCN):
    """CentralNode TelescopeOff for Mid."""

    def __init__(
        self,
        command_runtime_context: MidTelescopeOffContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
    ) -> None:
        super().__init__(command_runtime_context, adapter_provider, logger)
        # override the default executor
        self.executor = TelescopeOffExecutor(
            adapter_provider=adapter_provider,
            logger=logger,
        )

    def build_device_commands(self) -> None:
        """Build Phase 1: subarray Off commands only.

        Phase 2 commands (dishes, CSP, SDP) are built and executed
        inside ``invoke()`` after subarrays reach EMPTY obsState.
        """
        if self._plan is None:
            self.logger.error(
                "Command ID: %s | TelescopeOff plan is None",
                self.context.command_id,
            )
            return

        # Phase 1: Off on subarrays
        for target in self._plan.subarray_off_targets:
            self.context.device_commands.append(
                self._build_off_command(target, AdapterType.SUBARRAY)
            )

        self.logger.info(
            "Command ID: %s | TelescopeOff (Mid) Phase 1 "
            "device commands built: %s",
            self.context.command_id,
            [dc.device_name for dc in self.context.device_commands],
        )

    def invoke(self) -> None:
        """Two-phase execution for Mid TelescopeOff.

        Phase 1: Execute subarray Off commands (already built).
        Wait:    Wait for subarrays to reach EMPTY obsState.
        Phase 2: Build and execute dishes, CSP, SDP Off commands.
        """
        if self._plan is None:
            self.logger.error(
                "Command ID: %s | TelescopeOff plan is None in invoke",
                self.context.command_id,
            )
            return

        # Phase 1: Execute subarray Off commands
        if self.context.device_commands:
            self.executor.execute(self.context)

        # Check for subarray failures
        for _dev, result in (self.context.results or {}).items():
            result_code = getattr(result, "result_code", None)
            if result_code == ResultCode.FAILED:
                self._immediate_result = (
                    ResultCode.FAILED,
                    getattr(result, "message", "Subarray Off failed"),
                )
                return

        # Wait for subarrays to reach EMPTY
        wait_result = self._wait_for_subarray_empty()
        if wait_result[0] == ResultCode.FAILED:
            self._immediate_result = wait_result
            return

        # Phase 2: Build dish + CSP + SDP commands
        self.context.device_commands.clear()

        # Dishes Off
        for dish_name in self._plan.dish_off_targets:
            self.context.device_commands.append(
                self._build_off_command(dish_name, AdapterType.DISH)
            )

        # CSP and SDP Off (only available targets are in off_targets)
        for target in self._plan.off_targets:
            adapter_type = self._resolve_adapter_type(target)
            self.context.device_commands.append(
                self._build_off_command(target, adapter_type)
            )

        self.logger.info(
            "Command ID: %s | TelescopeOff (Mid) Phase 2 "
            "device commands built: %s",
            self.context.command_id,
            [dc.device_name for dc in self.context.device_commands],
        )

        # Execute Phase 2
        if self.context.device_commands:
            self.executor.execute(self.context)

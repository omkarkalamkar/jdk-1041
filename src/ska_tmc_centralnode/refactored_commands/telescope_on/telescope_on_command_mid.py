"""TelescopeOnMid – Mid-specific TelescopeOn command."""

from __future__ import annotations

import logging

from ska_tmc_common import AdapterFactory

from .telescope_on_command import BaseTelescopeOnCN
from .telescope_on_context import MidTelescopeOnContext
from .telescope_on_executor import TelescopeOnExecutor


class TelescopeOnMid(BaseTelescopeOnCN):
    """CentralNode TelescopeOn for Mid."""

    def __init__(
        self,
        command_runtime_context: MidTelescopeOnContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
    ) -> None:
        super().__init__(command_runtime_context, adapter_provider, logger)
        # override the default executor
        self.executor = TelescopeOnExecutor(
            adapter_provider=adapter_provider,
            logger=logger,
        )

    def build_device_commands(self) -> None:
        """Build the ordered list of DeviceCommands for Mid."""
        if self._plan is None:
            self.logger.error(
                "Command ID: %s | TelescopeOn plan is None",
                self.context.command_id,
            )
            return

        # 1. SetStandbyFPMode on selected dishes
        for dish_name in self._plan.standby_fp_targets:
            self.context.device_commands.append(
                self._build_set_standby_fp_command(dish_name)
            )

        # 2. On commands (CSP, SDP, Subarrays)
        for target in self._plan.on_targets:
            adapter_type = self._resolve_adapter_type(target)
            self.context.device_commands.append(
                self._build_on_command(target, adapter_type)
            )

        self.logger.info(
            "Command ID: %s | TelescopeOn (Mid) device commands built: %s",
            self.context.command_id,
            [dc.device_name for dc in self.context.device_commands],
        )

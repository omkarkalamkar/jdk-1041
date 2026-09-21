"""TelescopeOnLow – Low-specific TelescopeOn command."""

from __future__ import annotations

import logging

from ska_tmc_common import AdapterFactory

from .telescope_on_command import BaseTelescopeOnCN
from .telescope_on_context import LowTelescopeOnContext


class TelescopeOnLow(BaseTelescopeOnCN):
    """CentralNode TelescopeOn for Low."""

    def __init__(
        self,
        command_runtime_context: LowTelescopeOnContext,
        adapter_provider: AdapterFactory,
        logger: logging.Logger,
    ) -> None:
        super().__init__(command_runtime_context, adapter_provider, logger)

    def build_device_commands(self) -> None:
        """Build the ordered list of DeviceCommands for Low."""
        if self._plan is None:
            self.logger.error(
                "Command ID: %s | TelescopeOn plan is None",
                self.context.command_id,
            )
            return

        for target in self._plan.on_targets:
            adapter_type = self._resolve_adapter_type(target)
            self.context.device_commands.append(
                self._build_on_command(target, adapter_type)
            )

        self.logger.info(
            "Command ID: %s | TelescopeOn (Low) device commands built: %s",
            self.context.command_id,
            [dc.device_name for dc in self.context.device_commands],
        )

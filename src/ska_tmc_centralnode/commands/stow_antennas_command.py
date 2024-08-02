"""Command class for StowAntennas()"""
from typing import List, Tuple

from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import AdapterFactory, AdapterType
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from ska_tmc_centralnode.commands.central_node_command import (
    CentralNodeCommand,
)

# pylint:disable=abstract-method


class StowAntennas(CentralNodeCommand):
    """
    A class for CentralNode's StowAntennas() command.

    Invokes the command SetStowMode on the specified receptors.

    """

    def __init__(
        self,
        target,
        pop_state_model,
        adapter_factory=None,
        *args,
        logger=None,
        **kwargs,
    ):
        # pylint:disable=keyword-arg-before-vararg
        super().__init__(target, args, logger, kwargs)
        self.op_state_model = pop_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.dish_adapters = []
        self.init_adapters()

    def check_allowed(self):
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the
        component needed for the operation are not faulty

        :return: True if this command is allowed

        :rtype: boolean

        """
        if self.op_state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            raise CommandNotAllowed(
                "StowAntennas() is not allowed in current state :"
                f"{self.op_state_model.op_state}",
            )

        # for this command I need a number of sub-devices
        component_manager = self.target
        component_manager.check_if_dishes_are_responsive()

        return True

    def init_adapters(self):
        self.dish_adapters = []

        error_dev_names = []
        num_working = 0

        component_manager = self.target

        for dev_name in component_manager.input_parameter.dish_dev_names:
            devInfo = component_manager.get_device(dev_name)
            if not devInfo.unresponsive:
                try:
                    self.dish_adapters.append(
                        self._adapter_factory.get_or_create_adapter(
                            dev_name, AdapterType.DISH
                        )
                    )
                    num_working += 1
                except Exception as e:
                    self.logger.warning(
                        "Error in creating adapter for %s: %s", dev_name, e
                    )
                    error_dev_names.append(dev_name)

        if num_working == 0:
            return (
                ResultCode.FAILED,
                f"Error in creating dish adapters {'.'.join(error_dev_names)}",
            )

        return ResultCode.OK, ""

    # pylint:disable=signature-differs
    def do(self, argin: List[str]) -> Tuple[ResultCode, str]:
        """
        Method to invoke StowAntennas command.

        param argin:
            List of Receptors to be stowed.

        """

        for arg in argin:
            for adapter in self.dish_adapters:
                if arg not in adapter.dev_name:
                    continue
                (
                    return_codes,
                    message_or_unique_ids,
                ) = self.set_stow_mode_dishes(adapter)
                for return_code, message_or_unique_id in zip(
                    return_codes, message_or_unique_ids
                ):
                    if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                        return ResultCode.FAILED, message_or_unique_id
                    self.logger.error(
                        "Failed to stow receptor: %s with message: %s",
                        arg,
                        message_or_unique_id,
                    )
        return (ResultCode.OK, "Command Completed")

    def set_stow_mode_dishes(self, adapters):
        """Method for set stow mode for dish"""
        return self.send_command(
            [adapters],
            "Error in calling StowAntennasCommand() on TMC Dish leaf node",
            "SetStowMode",
        )

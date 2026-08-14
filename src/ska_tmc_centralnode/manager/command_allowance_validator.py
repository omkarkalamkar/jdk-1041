"""Command allowance validation collaborator for CentralNode."""
from logging import Logger
from typing import Any, Callable, List, Union, cast

from ska_control_model import AdminMode, ObsState
from ska_tango_base.faults import StateModelError
from ska_tmc_common import (
    AdapterFactory,
    AdapterType,
    CommandNotAllowed,
    DeviceInfo,
    SubarrayNotPresentError,
)
from tango import DevState
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from ska_tmc_centralnode.model.input import (
    InputParameterLow,
    InputParameterMid,
)


class CommandAllowanceValidator:
    """Validates whether a command is allowed for a CentralNode."""

    def __init__(
        self,
        logger: Logger,
        get_device: Callable[[str], DeviceInfo],
        input_parameter: Union[InputParameterMid, InputParameterLow],
        subarray_trl_prefix: str,
        retry_attempts: int,
        retry_delay: float,
        adapter_factory: AdapterFactory,
        get_op_state_model: Callable,
    ) -> None:
        self.input_parameter = input_parameter
        self.get_device: Callable[[str], DeviceInfo] = get_device
        self.logger = logger
        self.subarray_trl_prefix = subarray_trl_prefix
        self.supported_commands_for_responsive_check = [
            "TelescopeOn",
            "TelescopeOff",
            "TelescopeStandby",
            "AssignResources",
            "ReleaseResources",
        ]
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.adapter_factory = adapter_factory
        self.get_op_state_model = get_op_state_model

    def _get_subarray_name_by_id(self, subarray_id: int) -> str:
        """Provides full Subarray FQDN based on subarray id provided.

        Raises SubarrayNotPresentError, if the subarray is not present
        in the subarray device list.

        :param subarray_id: Subarray ID.
        :type subarray_id: int
        :return: Returns subarray full FQDN.
        :rtype: str
        """

        subarray_fqdn: str = self.subarray_trl_prefix + str(subarray_id).zfill(
            2
        )
        if subarray_fqdn not in self.input_parameter.subarray_dev_names:
            raise SubarrayNotPresentError(
                f"Subarray devices not available: {subarray_fqdn}"
            )
        return subarray_fqdn

    def is_command_allowed_before_lrc_start(
        self,
        subarray_id: int = 0,
        command_name: str = "",
    ):
        """This method checks if command is allowed before LRC start

        Args:
            subarray_id (int): subarray_id
            command_name (str): command name

        Returns:
            boolean value if command in valid obstate else
            return exception.

        Raises:
            StateModelError: If command not permitted in observation state
            SubarrayNotPresentError: If subarray not available
            CommandNotAllowed: If command not allowed due to other
                unavailable devices

        """
        self.logger.debug("Checking the devices for: %s", command_name)
        if command_name in self.supported_commands_for_responsive_check:
            self.check_device_responsiveness_command(subarray_id)
        allowed_obs_states = {
            "AssignResources": [ObsState.EMPTY, ObsState.IDLE],
            "ReleaseResources": [ObsState.IDLE],
        }
        if command_name in allowed_obs_states:
            desired_obsstate = allowed_obs_states.get(command_name)
        else:
            desired_obsstate = None
        if subarray_id and desired_obsstate:
            subarray_fqdn: str = self._get_subarray_name_by_id(subarray_id)
            subarray_obstate = self.get_device(subarray_fqdn).obs_state
            if subarray_obstate not in desired_obsstate:
                raise StateModelError(
                    f"{command_name} command not permitted "
                    + f"in observation state {subarray_obstate}"
                )
        return True

    def check_device_responsiveness_command(self, subarray_id: int) -> None:
        """
        Override this method to add responsive checks for the devices

        Args:
            subarray_id (int): Subarray id

        """
        subarray_devices: list = self.input_parameter.subarray_dev_names
        if subarray_id:
            subarray_fqdn: str = self._get_subarray_name_by_id(subarray_id)
            subarray_devices = [subarray_fqdn]
        self._check_if_device_is_responsive(subarray_devices)

    def _is_subarray_node_in_devices(self, device_names: list) -> bool:
        """Checks whether subarray node is present in device names.

        :param device_names: List of device names.
        :type device_names: list
        :return: Returns True if subarray node is present
        in devices, else False.
        :rtype: bool
        """
        return any(
            name in self.input_parameter.subarray_dev_names
            for name in device_names
        )

    def _get_unresponsive_devices(self, device_names: list) -> list[str]:
        """Provides list of unresponsive devices.

        :param device_names: List of devices.
        :type device_names: list
        :return: List of unresponsive devices.
        :rtype: list[str]
        """
        unresponsive_devices: list = []
        for dev_name in device_names:
            dev_info = self.get_device(dev_name)
            if not dev_info or dev_info.unresponsive:
                unresponsive_devices.append(dev_name)
            else:
                self.logger.debug(
                    f"Device {dev_name} dev_info.unresponsive:"
                    + f" {dev_info.unresponsive} "
                )
        return unresponsive_devices

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(3.0),
        retry=retry_if_exception_type(
            (CommandNotAllowed, SubarrayNotPresentError)
        ),
        reraise=True,
    )
    def _check_if_device_is_responsive(self, dev_names: List[str]):
        """checks if the device is responsive"""

        cast(
            Any, self._check_if_device_is_responsive
        ).retry.stop = stop_after_attempt(self.retry_attempts)
        cast(Any, self._check_if_device_is_responsive).retry.wait = wait_fixed(
            self.retry_delay
        )
        self.logger.debug("Retrying device responsive check")
        unresponsive_devices = self._get_unresponsive_devices(dev_names)

        # Raise SubarrayNotPresentError if fqdn matches subarray prefix,
        # else CommandNotAllowed
        if unresponsive_devices:
            if self._is_subarray_node_in_devices(unresponsive_devices):
                raise SubarrayNotPresentError(
                    f"Subarray devices not available: {unresponsive_devices}"
                )
            raise CommandNotAllowed(f"{unresponsive_devices} not available")

    def get_sdp_controller_admin_mode(self) -> AdminMode:
        """
        Retrieve the adminMode of sdp controller.

        Returns:
            This method returns the adminMode of the
            TMC sdp controller leaf Node.
        """
        sdp_mln_adapter = self.adapter_factory.get_or_create_adapter(
            self.input_parameter.sdp_mln_dev_name,
            adapter_type=AdapterType.SDP_MASTER_LEAF_NODE,
        )
        return sdp_mln_adapter.sdpControllerAdminMode

    def get_csp_controller_admin_mode(self) -> AdminMode:
        """
        Retrieve the adminMode of CSP controller.

        Returns:
            str: The adminMode of the TMC CSP controller Leaf Node.
        """
        csp_mln_adapter = self.adapter_factory.get_or_create_adapter(
            self.input_parameter.csp_mln_dev_name,
            adapter_type=AdapterType.CSP_MASTER_LEAF_NODE,
        )
        return csp_mln_adapter.cspControllerAdminMode

    def _get_admin_modes(self) -> dict:
        """Provides the admin modes for respective subsystems.

        :return: Returns admin mode of subsystems.
        :rtype: dict
        """
        return {
            "SDP": self.get_sdp_controller_admin_mode(),
            "CSP": self.get_csp_controller_admin_mode(),
        }

    def is_valid_admin_mode(self) -> bool:
        """
        Extends the base admin mode validation with MCCS
        check for LOW telescope.

        Returns:
            bool: True if all controllers including MCCS
            are in valid admin mode.
        """

        admin_modes = self._get_admin_modes()
        if any(
            mode in [AdminMode.OFFLINE, AdminMode.NOT_FITTED]
            for _, mode in admin_modes.items()
        ):
            self.logger.debug("AdminMode check failed: %s", admin_modes)
            return False

        return True

    def _check_op_state(self, command_name: str) -> None:
        """Check if the operational state is valid to proceed
        with command execution.

        :param command_name: Name of the command.
        :type command_name: str
        :raises CommandNotAllowed: Raises command not allowed if the
        operational is invalid.
        """
        if self.get_op_state_model().op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            self.logger.warning(
                f"{command_name} command is not supported "
                + f"in {self.get_op_state_model().op_state} for CentralNode"
            )
            raise CommandNotAllowed(
                "Command is not allowed in current state :"
                + f"{str(self.get_op_state_model().op_state)}",
            )


class LowCommandAllowanceValidator(CommandAllowanceValidator):
    """Validates whether a command is allowed for a CentralNode in Low
    telescope."""

    def check_device_responsiveness_command(self, subarray_id: int) -> None:
        """
        This method overrides the method from super class
        to add responsive checks for the devices

        Args:
            subarray_id (int): Subarray id

        """
        super().check_device_responsiveness_command(subarray_id)
        self.check_if_mccs_mln_is_responsive()

    def check_if_mccs_mln_is_responsive(self):
        """Checks whether mccs mln is responsive"""
        return self._check_if_device_is_responsive(
            [self.input_parameter.mccs_mln_dev_name]
        )

    def get_mccs_controller_admin_mode(self) -> AdminMode:
        """
        Retrieve the adminMode of mccs controller.

        Returns:
            This method returns the adminMode of the
            TMC mccs controller leaf Node.

        """
        input_param = cast(InputParameterLow, self.input_parameter)
        mccs_mln_adapter = self.adapter_factory.get_or_create_adapter(
            input_param.mccs_mln_dev_name,
            adapter_type=AdapterType.MCCS_MASTER_LEAF_NODE,
        )
        return mccs_mln_adapter.mccsControllerAdminMode

    def _get_admin_modes(self) -> dict:
        """Provides the admin modes for respective subsystems.

        :return: Returns admin mode of subsystems.
        :rtype: dict
        """
        admin_modes = super()._get_admin_modes()
        admin_modes["MCCS"] = self.get_mccs_controller_admin_mode()
        return admin_modes

    def is_command_allowed(self, command_name=None) -> bool:
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the
        component needed for the operation are not unresponsive

        :param command_name: name of the command
        :type command_name: str
        :return: True if this command is allowed

        :rtype: boolean
        """
        if not self.is_valid_admin_mode():
            raise CommandNotAllowed(
                "One or more controller devices are in "
                "adminMode OFFLINE or NOT-FITTED"
            )
        self._check_op_state(command_name)
        return True


class MidCommandAllowanceValidator(CommandAllowanceValidator):
    """Validates whether a command is allowed for a CentralNode in Mid
    telescope."""

    def __init__(
        self,
        logger,
        get_device,
        input_parameter,
        subarray_trl_prefix,
        retry_attempts,
        retry_delay,
        adapter_factory,
        get_op_state_model,
        dish_vcc_init_enabled,
        get_dish_vcc_config_set,
    ) -> None:
        super().__init__(
            logger,
            get_device,
            input_parameter,
            subarray_trl_prefix,
            retry_attempts,
            retry_delay,
            adapter_factory,
            get_op_state_model,
        )
        self.dish_vcc_init_enabled: bool = dish_vcc_init_enabled
        self.get_dish_vcc_config_set: Callable = get_dish_vcc_config_set

    def check_device_responsiveness_command(self, subarray_id: int) -> None:
        """
        This method overrides the method from super class
        to add responsive checks for the devices

        Args:
            subarray_id (int): Subarray id

        """
        super().check_device_responsiveness_command(subarray_id)
        self.check_if_dishes_are_responsive()

    def check_if_dishes_are_responsive(self) -> bool:
        """
        Checks whether dishes are responsive

        Returns:
            True, if dishes are responsive,
            False otherwise

        """
        input_param = cast(InputParameterMid, self.input_parameter)
        self.logger.debug("Checking if dishes are responsive")
        return self._check_if_device_is_responsive(
            input_param.dish_leaf_node_dev_names
        )

    def is_command_allowed(self, command_name=None) -> bool:
        """
        Checks whether this command is allowed
        It checks that the device is in a state
        to perform this command and that all the
        component needed for the operation are not unresponsive

        Args:
            command_name (str): name of the command

        Returns:
            True if this command is allowed

        """
        if not self.is_valid_admin_mode():
            raise CommandNotAllowed(
                "One or more controller devices are in "
                "adminMode OFFLINE or NOT-FITTED"
            )

        if self.dish_vcc_init_enabled:
            if not self.get_dish_vcc_config_set() and command_name not in [
                "TelescopeOff",
                "TelescopeStandby",
                "LoadDishCfg",
            ]:
                raise CommandNotAllowed(
                    "Dish Vcc Config not Set. Please set using LoadDishCfg"
                    " command. "
                    "Current Telescope State is :"
                    + f"{str(self.get_op_state_model().op_state)}",
                )
        self._check_op_state(command_name)
        return True

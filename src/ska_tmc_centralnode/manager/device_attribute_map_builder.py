"""Device-attribute subscription map builder for SubarrayNode."""

from collections import defaultdict
from logging import Logger
from typing import Dict, List

from ska_tmc_common import DeviceInfo

from ska_tmc_centralnode.model.input import InputParameterMid
from ska_tmc_centralnode.utils.constants import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MCCS_MLN_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
)

_COMMON_ATTRIBUTES = [
    "state",
    "healthState",
    "adminMode",
]
_SUBARRAYS_ATTRIBUTES = [
    "assignedResources",
    "obsState",
]
_DISHLN_ATTRIBUTES = [
    "dishMode",
    "kValueValidationResult",
    "healthState",
    "gpmVersion",
]

_SUBARRAY_NODE_ONLY_ATTRIBUTES = [
    "isSubarrayAvailable",
]
_CSP_CONTROLLER_ADMIN_MODE = "cspControllerAdminMode"
_SDP_CONTROLLER_ADMIN_MODE = "sdpControllerAdminMode"
_MCCS_CONTROLLER_ADMIN_MODE = "mccsControllerAdminMode"

_MID_CSP_MLN_ATTRIBUTES = [
    "DishVccMapValidationResult",
    _CSP_CONTROLLER_ADMIN_MODE,
]


class DeviceAttributeMapBuilder:
    """Builds device-to-attributes subscription mapping."""

    def __init__(self, logger: Logger, input_parameter):
        self.logger = logger
        self.input_parameter = input_parameter

    def _is_subarray(self, name: str) -> bool:
        """Verifies if the device name is of subarray not a leaf node.

        :param name: _description_
        :type name: str
        :return: _description_
        :rtype: bool
        """
        return "subarray" in name and "leaf" not in name

    def _is_dish_leaf_node(self, name: str) -> bool:
        """Verifies if the device name is of dish leaf node.

        :param name: _description_
        :type name: str
        :return: _description_
        :rtype: bool
        """
        return (
            isinstance(self.input_parameter, InputParameterMid)
            and name in self.input_parameter.dish_leaf_node_dev_names
        )

    def _add_common_attributes(
        self, device_name: str, device_attribute_map: dict
    ) -> None:
        """Adds the common attribute list for all devices.

        :param device_attribute_map: Dictionary containing device and its
        attributes that needs to be subscribed.
        :type device_attribute_map: dict
        :param device_name: device FQDN
        :type device_name: str
        """
        device_attribute_map[device_name].extend(_COMMON_ATTRIBUTES)

    def _add_subarray_attributes(
        self, device_name: str, device_attribute_map: dict
    ) -> None:
        """Adds the attribute related to subarray.

        :param device_attribute_map: Dictionary containing device and its
        attributes that needs to be subscribed.
        :type device_attribute_map: dict
        :param device_name: device FQDN
        :type device_name: str
        """
        if self._is_subarray(device_name):
            device_attribute_map[device_name].extend(_SUBARRAYS_ATTRIBUTES)

    def _add_dishln_attributes(
        self, device_name: str, device_attribute_map: dict
    ) -> None:
        """Adds the attribute related to dish leaf node.

        :param device_attribute_map: Dictionary containing device and its
        attributes that needs to be subscribed.
        :type device_attribute_map: dict
        :param device_name: device FQDN
        :type device_name: str
        """
        if self._is_dish_leaf_node(device_name):
            device_attribute_map[device_name].extend(_DISHLN_ATTRIBUTES)

    def _add_subarray_node_attributes(
        self, device_name: str, device_attribute_map: dict
    ) -> None:
        """Adds the attribute related to subarray node.

        :param device_attribute_map: Dictionary containing device and its
        attributes that needs to be subscribed.
        :type device_attribute_map: dict
        :param device_name: device FQDN
        :type device_name: str
        """
        if device_name in self.input_parameter.subarray_dev_names:
            device_attribute_map[device_name].extend(
                _SUBARRAY_NODE_ONLY_ATTRIBUTES
            )

    def _add_availability_attributes(
        self, device_name: str, device_attribute_map: dict
    ) -> None:
        """Adds the availability attribute for only certain devices.

        :param device_attribute_map: Dictionary containing device and its
        attributes that needs to be subscribed.
        :type device_attribute_map: dict
        :param device_name: device FQDN
        :type device_name: str
        """
        subsystem_devices = [
            MID_CSP_MLN_DEVICE,
            MID_SDP_MLN_DEVICE,
            LOW_CSP_MLN_DEVICE,
            LOW_SDP_MLN_DEVICE,
            MCCS_MLN_DEVICE,
        ]
        if device_name in subsystem_devices:
            device_attribute_map[device_name].append("isSubsystemAvailable")

    def _add_admin_mode_attributes(self, device_attribute_map: dict) -> None:
        """Adds the admin mode related attributes specific to subsystems.

        :param device_attribute_map: Dictionary containing device and its
        attributes that needs to be subscribed.
        :type device_attribute_map: dict
        """

        if MID_CSP_MLN_DEVICE in device_attribute_map:
            device_attribute_map[MID_CSP_MLN_DEVICE].extend(
                _MID_CSP_MLN_ATTRIBUTES
            )
        if LOW_CSP_MLN_DEVICE in device_attribute_map:
            device_attribute_map[LOW_CSP_MLN_DEVICE].append(
                _CSP_CONTROLLER_ADMIN_MODE
            )
        if MID_SDP_MLN_DEVICE in device_attribute_map:
            device_attribute_map[MID_SDP_MLN_DEVICE].append(
                _SDP_CONTROLLER_ADMIN_MODE
            )
        if LOW_SDP_MLN_DEVICE in device_attribute_map:
            device_attribute_map[LOW_SDP_MLN_DEVICE].append(
                _SDP_CONTROLLER_ADMIN_MODE
            )
        if MCCS_MLN_DEVICE in device_attribute_map:
            device_attribute_map[MCCS_MLN_DEVICE].extend(
                [_MCCS_CONTROLLER_ADMIN_MODE]
            )

    def build(self, devices: List[DeviceInfo]) -> Dict[str, List[str]]:
        """
        Builds a dictionary mapping device names to lists of attributes
        to be subscribed.

        Returns:
            Dict[str, List[str]]: A mapping from device names to list of
            attributes.
        """
        device_attribute_map: Dict[str, List] = defaultdict(list)

        for dev_info in devices:
            dev_name = dev_info.dev_name
            # Add basic attributes to all devices
            self._add_common_attributes(dev_name, device_attribute_map)

            # Subarray-specific attributes (excluding leaf nodes)
            self._add_subarray_attributes(dev_name, device_attribute_map)

            # Dish leaf node-specific attributes
            self._add_dishln_attributes(dev_name, device_attribute_map)

            # Subarray dev-specific attributes
            self._add_subarray_node_attributes(dev_name, device_attribute_map)

            # Subsystem availability attribute
            self._add_availability_attributes(dev_name, device_attribute_map)

        # Add specific subsystem attributes if present
        self._add_admin_mode_attributes(device_attribute_map)

        self.logger.debug(
            "Device attribute map dictionary : %s", device_attribute_map
        )
        return device_attribute_map

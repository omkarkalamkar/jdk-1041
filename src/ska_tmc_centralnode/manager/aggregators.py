"""Aggregation method for telescope state Aggregating for Mid"""

import logging
from typing import Dict, List, Set, cast

from ska_ser_logging import configure_logging
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DeviceInfo
from ska_tmc_common.aggregators import Aggregator
from ska_tmc_common.enum import DishMode
from tango import DevState

from ska_tmc_centralnode.manager.component_manager_config import DishVccConfig
from ska_tmc_centralnode.utils.constants import (
    DISH_KVALUE_VALIDATION_RESULT_STATUS,
)

configure_logging("DEBUG")

LOGGER = logging.getLogger(__name__)


class TelescopeStateAggregatorMid(Aggregator):
    """Class for TelescopeStateAggregation for Mid Telescope"""

    def __init__(self, cm, logger) -> None:
        self.logger = logger
        super().__init__(cm, logger)

    def _update_state_dish_mode(
        self,
        dish_modes: Set[DishMode],
        subsystem_states: Set[DevState],
        master_device_availability: Dict[str, bool],
    ) -> None:
        """Update state, dish mode and master device availability.

        :param dish_modes: Set of dish modes.
        :type dish_modes: Set[DishMode]
        :param subsystem_states: Set of device states.
        :type subsystem_states: Set[DevState]
        :param master_device_availability: Dictionary with subsystem master
        device availability.
        :type master_device_availability: Dict[str, bool]
        """
        for device in self._component_manager.checked_devices:
            name = device.dev_name
            if device.unresponsive:
                continue
            if (
                name
                in self._component_manager.get_dish_leaf_node_device_names()
            ):
                dish_modes.add(device.dish_mode)
            elif (
                name
                == self._component_manager.input_parameter.csp_master_dev_name
            ):
                subsystem_states.add(device.state)
                master_device_availability["CSP"] = True
            elif (
                name
                == self._component_manager.input_parameter.sdp_master_dev_name
            ):
                subsystem_states.add(device.state)
                master_device_availability["SDP"] = True

    def _is_state_unknown(
        self,
        dish_modes: Set[DishMode],
        master_device_availability: Dict[str, bool],
    ) -> bool:
        """Checks whether devstate UNKNOWN needs to be set.

        :param dish_modes: Dish Modes.
        :type dish_modes: Set[DishMode]
        :param master_device_availability: Dictionary with subsystem master
        device availability.
        :type master_device_availability: Dict[str, bool]
        :return: Returns True if state UNKNOWN needs to be set.
        :rtype: bool
        """
        # If Dish VCC config is not set then set telescope state to UNKNOWN
        if cast(
            DishVccConfig, self._component_manager.config.dish_config
        ).enable_init:
            if not self._component_manager.is_dish_vcc_config_set:
                return True
        if not all(master_device_availability.values()):
            self._logger.debug(
                "Checking if sdp and csp master are responsive: "
                + "%s,responsive : %s "
                + "%s, responsive: %s ",
                self._component_manager.input_parameter.sdp_master_dev_name,
                master_device_availability.get("SDP"),
                self._component_manager.input_parameter.csp_master_dev_name,
                master_device_availability.get("CSP"),
            )
            return True
        if not dish_modes:
            return True
        return False

    def aggregate(self) -> DevState:
        """
        Aggregate method for TelescopeStateAggregateMid

        Returns:
            DevState: Aggregates TelescopeState for mid

        """
        subsystem_states: Set[DevState] = set()
        dish_modes: Set[DishMode] = set()
        master_device_availability: Dict[str, bool] = dict.fromkeys(
            ["CSP", "SDP"], False
        )
        self._update_state_dish_mode(
            dish_modes, subsystem_states, master_device_availability
        )
        self._logger.debug(
            "telescopeSetStateset : %s , dishmodeset : "
            + "%s dish_vcc_config_set: %s",
            str(subsystem_states),
            str(dish_modes),
            self._component_manager.is_dish_vcc_config_set,
        )
        if self._is_state_unknown(dish_modes, master_device_availability):
            return DevState.UNKNOWN

        usable_dish_modes = {
            DishMode.STANDBY_FP,
            DishMode.OPERATE,
            DishMode.CONFIG,
        }
        has_usable_dish = any(mode in usable_dish_modes for mode in dish_modes)
        if subsystem_states == {DevState.ON} and has_usable_dish:
            return DevState.ON
        if (
            subsystem_states == {DevState.OFF}
            and dish_modes == {DishMode.STANDBY_LP}
            or dish_modes == {DishMode.SHUTDOWN}
        ):
            return DevState.OFF
        if DevState.INIT in subsystem_states:
            return DevState.INIT
        if DevState.FAULT in subsystem_states:
            return DevState.FAULT
        if DevState.STANDBY in subsystem_states and dish_modes == {
            DishMode.STANDBY_LP
        }:
            return DevState.STANDBY
        return DevState.UNKNOWN


class TelescopeStateAggregatorLow(Aggregator):
    """Class for TelescopeStateAggregation for low Telescope"""

    def __init__(self, cm, logger) -> None:
        self.logger = logger
        super().__init__(cm, logger)

    def _update_state_availability(
        self,
        telescope_state_list: List[DevState],
        master_device_availability: Dict[str, bool],
    ) -> None:
        """Updates device state and availability in respective data structures.

        :param telescope_state_list: list of device states
        :type telescope_state_list: List[DevState]
        :param master_device_availability: Dictionary with subsystem master
        device availability.
        :type master_device_availability:  Dict[str,bool]
        """
        for device in self._component_manager.checked_devices:
            name = device.dev_name.lower()
            if device.unresponsive:
                continue
            if (
                name
                == self._component_manager.input_parameter.mccs_master_dev_name
            ):
                telescope_state_list.append(device.state)
                master_device_availability["MCCS"] = True
            elif (
                name
                == self._component_manager.input_parameter.csp_master_dev_name
            ):
                telescope_state_list.append(device.state)
                master_device_availability["CSP"] = True
            elif (
                name
                == self._component_manager.input_parameter.sdp_master_dev_name
            ):
                telescope_state_list.append(device.state)
                master_device_availability["SDP"] = True

    def aggregate(self) -> DevState:
        """
        Aggregate method for TelescopeStateAggregatorLow

        Returns:
            DevState: Aggregates TeleScopeState for low

        """
        telescope_state_list: List[DevState] = []
        master_device_availability: Dict[str, bool] = dict.fromkeys(
            ["CSP", "SDP"], False
        )
        self._update_state_availability(
            telescope_state_list, master_device_availability
        )
        telescope_set_state = set(telescope_state_list)
        self._logger.debug(
            "Telescope state list is : %s", str(telescope_state_list)
        )
        if not all(master_device_availability.values()):
            self._logger.debug(
                "Checking if sdp, csp and mccs master are responsive: "
                + "%s , responsive :%s,"
                + "%s, responsive : %s"
                + "%s, responsive : %s",
                self._component_manager.input_parameter.sdp_master_dev_name,
                master_device_availability.get("SDP"),
                self._component_manager.input_parameter.csp_master_dev_name,
                master_device_availability.get("CSP"),
                self._component_manager.input_parameter.mccs_master_dev_name,
                master_device_availability.get("MCCS"),
            )
            return DevState.UNKNOWN
        if telescope_set_state == {DevState.ON}:
            return DevState.ON
        if telescope_set_state == {DevState.OFF}:
            return DevState.OFF
        if DevState.INIT in telescope_set_state:
            return DevState.INIT
        if DevState.FAULT in telescope_set_state:
            return DevState.FAULT
        if DevState.STANDBY in telescope_set_state:
            return DevState.STANDBY
        return DevState.UNKNOWN


class TMCOpStateAggregator(Aggregator):
    """Class for TelescopeOpStateAggregation for low Telescope"""

    def __init__(self, cm, logger) -> None:
        self.logger = logger
        super().__init__(cm, logger)

    def aggregate(self) -> DevState:
        """
        Aggregate method for TMC Op State

        Returns:
            DevState: Aggregates TMC Op state

        """
        tmc_state_list: List[DevState] = []
        # get states of all TM devices
        # what if one of them is not working? i.e. tm subarray
        # number of devices is also variable, how to handle that number
        for device in self._component_manager.checked_devices:
            name = device.dev_name.lower()
            if "tm" in name:
                if device.unresponsive:
                    continue
                tmc_state_list.append(device.state)

        tmc_set_state = set(tmc_state_list)
        if tmc_set_state == {DevState.ON}:
            return DevState.ON
        if tmc_set_state == {DevState.OFF}:
            #  Untill all TMC devices are refactored, devices report Off state.
            return DevState.OFF
        if DevState.INIT in tmc_set_state:
            return DevState.INIT
        if DevState.FAULT in tmc_set_state:
            return DevState.FAULT
        return DevState.UNKNOWN


class TelescopeAvailabilityAggregator(Aggregator):
    """Class for TelescopeAvailablity for Telescope  MID and LOW."""

    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)
        self.logger = logger

    def _update_subarray_availability(
        self,
        device: DeviceInfo,
        telescope_availability: Dict[str, Dict[str, bool] | bool],
    ) -> None:
        """Update subarray availability.

        :param device: Instance of DevieInfo.
        :type device: DeviceInfo
        :param telescope_availability: Dictionary with availabilities.
        :type telescope_availability: dict
        """
        if device.unresponsive:
            cast(
                Dict[str, bool], telescope_availability["tmc_subarrays"]
            ).update({device.dev_name: False})
        else:
            availability: bool = (
                self._component_manager.subarray_availability.get(
                    device.dev_name, False
                )
            )
            cast(
                Dict[str, bool], telescope_availability["tmc_subarrays"]
            ).update({device.dev_name: availability})

    def _update_cspln_availability(
        self,
        device: DeviceInfo,
        telescope_availability: Dict[str, Dict[str, bool] | bool],
    ) -> None:
        """Update CSP master leaf node availability.

        :param device: Instance of DevieInfo.
        :type device: DeviceInfo
        :param telescope_availability: Dictionary with availabilities.
        :type telescope_availability: dict
        """
        if device.unresponsive:
            telescope_availability["csp_master_leaf_node"] = False
        else:
            telescope_availability["csp_master_leaf_node"] = (
                self._component_manager.csp_mln_availability
            )

    def _update_sdpln_availability(
        self,
        device: DeviceInfo,
        telescope_availability: Dict[str, Dict[str, bool] | bool],
    ) -> None:
        """Update SDP master leaf node availability.

        :param device: Instance of DevieInfo.
        :type device: DeviceInfo
        :param telescope_availability: Dictionary with availabilities.
        :type telescope_availability: dict
        """
        if device.unresponsive:
            telescope_availability["sdp_master_leaf_node"] = False
        else:
            telescope_availability["sdp_master_leaf_node"] = (
                self._component_manager.sdp_mln_availability
            )

    def update_availability(
        self,
        device: DeviceInfo,
        telescope_availability: Dict[str, Dict[str, bool] | bool],
    ) -> None:
        """Update SDP master leaf node availability.

        :param device: Instance of DevieInfo.
        :type device: DeviceInfo
        :param telescope_availability: Dictionary with availabilities.
        :type telescope_availability: dict
        """
        input_param = self._component_manager.input_parameter
        if device.dev_name in input_param.subarray_dev_names:
            self._update_subarray_availability(device, telescope_availability)
        elif device.dev_name.lower() in (input_param.csp_mln_dev_name.lower()):
            self._update_cspln_availability(device, telescope_availability)
        elif device.dev_name.lower() in (input_param.sdp_mln_dev_name.lower()):
            self._update_sdpln_availability(device, telescope_availability)

    def aggregate(self) -> None:
        """Aggregate method for Telescope Availability"""
        telescope_availability = (
            self._component_manager.get_telescope_availability()
        )
        for device in self._component_manager.checked_devices:
            self.update_availability(device, telescope_availability)

        self._component_manager.set_telescope_availability(
            telescope_availability
        )


class TelescopeAvailabilityAggregatorLow(TelescopeAvailabilityAggregator):
    """Class for TelescopeAvailablity for low Telescope"""

    def _update_mccsln_availability(
        self,
        device: DeviceInfo,
        telescope_availability: Dict[str, Dict[str, bool] | bool],
    ) -> None:
        """Update MCCS master leaf node availability.

        :param device: Instance of DevieInfo.
        :type device: DeviceInfo
        :param telescope_availability: Dictionary with availabilities.
        :type telescope_availability: dict
        """
        if device.unresponsive:
            telescope_availability["mccs_master_leaf_node"] = False
        else:
            telescope_availability["mccs_master_leaf_node"] = (
                self._component_manager.mccs_mln_availability
            )

    def update_availability(
        self,
        device: DeviceInfo,
        telescope_availability: Dict[str, Dict[str, bool] | bool],
    ) -> None:
        """Update SDP master leaf node availability.

        :param device: Instance of DevieInfo.
        :type device: DeviceInfo
        :param telescope_availability: Dictionary with availabilities.
        :type telescope_availability: dict
        """
        super().update_availability(device, telescope_availability)
        input_param = self._component_manager.input_parameter
        if device.dev_name.lower() in (input_param.mccs_mln_dev_name.lower()):
            self._update_mccsln_availability(device, telescope_availability)


class DishAttrValueAggregator:
    """This Class Aggregate k-value validation results
    received from Dish Leaf Nodes.
    """

    def __init__(self, cm, logger) -> None:
        """
        :param cm: Central Node Component Manager
        :param type: component manager
        :param logger: Logger
        """
        self._component_manager = cm
        self.logger = logger
        self.dln_kvalue_validation_results: Dict[str, str] = {}
        self.input_parameter_obj = self._component_manager.input_parameter

    def is_events_received_percentage_valid(self) -> bool:
        """
        Verify the percent of kvalue validation result event received
        as specified by DishKvalueAggregationAllowedPercent property.

        Returns:
            bool: `True`, if Events recieved percentage is valid.
            `False`, otherwise.

        """
        if self.dln_kvalue_validation_results:
            total_events = len(self.dln_kvalue_validation_results.values())
            percent_event_received = (
                total_events
                / len(self.input_parameter_obj.dish_leaf_node_dev_names)
            ) * 100
            config: DishVccConfig = self._component_manager.config.dish_config
            if (
                percent_event_received
                >= config.dish_k_value_aggregation_allowed_precent
            ):
                return True
        return False

    def update_central_node_with_result(self) -> None:
        """
        This method updates the DishVccValidationStatus of Central Node.
        """
        check_set_k_val_success_on_all_dln = set(
            self.dln_kvalue_validation_results.values()
        ) == {"k-value identical"}
        self.logger.debug(
            "kValueValidationResult dictionary: %s",
            self.dln_kvalue_validation_results.values(),
        )
        if not check_set_k_val_success_on_all_dln:
            is_set_k_value_successful = any(
                v == "k-value identical"
                for v in self.dln_kvalue_validation_results.values()
            )
            if is_set_k_value_successful:
                self._component_manager.is_dish_vcc_config_set = True
            else:
                self._component_manager.is_dish_vcc_config_set = False
            # Report dish leaf nodes with error.
            self._component_manager.dish_vcc_validation_status = (
                self.dln_kvalue_validation_results
            )
        else:
            self._component_manager.dish_vcc_validation_status = {
                "dish": "ALL DISH OK"
            }

    def aggregate(
        self, dish_leaf_node_fqdn: str, kvalue_validation_result: ResultCode
    ) -> None:
        """
        Aggregate the k-value validation result received from
        Dish leaf nodes and provide the aggregated k-value report
        result to Central Node.

        Args:
            dish_leaf_node_fqdn (str):
                dish leaf node fqdn
            kvalue_validation_result (ResultCode):
                kvalue validation result code

        """
        with self._component_manager.dish_vcc_validation_attr_lock:
            dish_leaf_node_name = dish_leaf_node_fqdn.split("/")[-1]
            dish_kvalue_validation_result = ResultCode(
                int(kvalue_validation_result)
            )
            self.dln_kvalue_validation_results[dish_leaf_node_name] = (
                DISH_KVALUE_VALIDATION_RESULT_STATUS[
                    dish_kvalue_validation_result
                ]
            )
            # Update the Central Node result attribute.
            self.update_central_node_with_result()

    def _update_unknown_dishes(self, gpm_unknown_dishes: List[str]) -> None:
        """Returns the list of unknown dishes."""
        initializing_gpm: bool = True
        for (
            dish_id,
            bands,
        ) in self._component_manager.global_pointing_model_status.items():
            if not isinstance(bands, str):
                for _, band_status in bands.items():
                    if band_status != "UNKNOWN":
                        initializing_gpm = False
                        break
            else:
                initializing_gpm = False
            if initializing_gpm:
                gpm_unknown_dishes.append(dish_id)
            initializing_gpm = True

    def aggregate_gpm(self) -> List[str]:
        """
        Aggregate the GPM version received from
        Dish leaf nodes and provide the list of DLN on which
        GPM is missing to Central Node.

        Args:
            dish_leaf_node_fqdn (str):
                dish leaf node fqdn
            gpm_version (dict):
                GPM version on dish leaf node

        """
        gpm_unknown_dishes: List[str] = []
        self.logger.debug(
            "Current GPM Status %s",
            self._component_manager.global_pointing_model_status,
        )
        total_events = len(
            self._component_manager.global_pointing_model_status.keys()
        )
        if total_events == len(
            self.input_parameter_obj.dish_leaf_node_dev_names
        ):
            self._update_unknown_dishes(gpm_unknown_dishes)
        self.logger.debug(
            "Dishes for which GPM version not set: %s", gpm_unknown_dishes
        )
        return gpm_unknown_dishes

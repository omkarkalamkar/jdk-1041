from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common.aggregators import Aggregator
from ska_tmc_common.enum import DishMode
from tango import DevState

from ska_tmc_centralnode.utils.constants import MCCS_MLN_SUFIX


class TelescopeStateAggregatorMid(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):
        # import debugpy; debugpy.debug_this_thread()
        subsystem_states = set()
        dish_modes = set()
        dish_count = 0
        csp_master = False
        sdp_master = False
        for dev in self._component_manager.checked_devices:
            name = dev.dev_name.lower()
            if dev.unresponsive:
                continue
            elif (
                name in self._component_manager.input_parameter.dish_dev_names
            ):
                dish_modes.add(dev.dish_mode)
                dish_count += 1
            elif (
                name
                == self._component_manager.input_parameter.csp_master_dev_name
            ):
                subsystem_states.add(dev.state)
                csp_master = True
            elif (
                name
                == self._component_manager.input_parameter.sdp_master_dev_name
            ):
                subsystem_states.add(dev.state)
                sdp_master = True

        self._logger.info(
            "telescopeSetStateset : %s , dishmodeset : %s ",
            subsystem_states,
            dish_modes,
        )
        if not sdp_master and not csp_master:
            self._logger.info(
                "missing devices: %s=%s %s=%s",
                self._component_manager.input_parameter.sdp_master_dev_name,
                sdp_master,
                self._component_manager.input_parameter.csp_master_dev_name,
                csp_master,
            )
            return DevState.UNKNOWN
        elif dish_count == 0:
            self._logger.info("dish_count == 0")
            return DevState.UNKNOWN
        elif subsystem_states == {DevState.ON} and dish_modes == {
            DishMode.STANDBY_FP
        }:
            return DevState.ON
        elif subsystem_states == {DevState.OFF} and dish_modes == {
            DishMode.STANDBY_LP
        }:
            return DevState.OFF
        elif DevState.INIT in subsystem_states:
            return DevState.INIT
        elif DevState.FAULT in subsystem_states:
            return DevState.FAULT
        elif (
            DevState.STANDBY in subsystem_states
            or DishMode.STANDBY_LP in dish_modes
        ):
            return DevState.STANDBY
        else:
            return DevState.UNKNOWN


class TelescopeStateAggregatorLow(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):
        telescopeStateList = []
        mccs_master = False
        csp_master = False
        sdp_master = False

        for dev in self._component_manager.checked_devices:
            name = dev.dev_name.lower()
            if dev.unresponsive:
                continue
            elif (
                name
                == self._component_manager.input_parameter.mccs_master_dev_name
            ):
                telescopeStateList.append(dev.state)
                mccs_master = True
            elif (
                name
                == self._component_manager.input_parameter.csp_master_dev_name
            ):
                telescopeStateList.append(dev.state)
                csp_master = True
            elif (
                name
                == self._component_manager.input_parameter.sdp_master_dev_name
            ):
                telescopeStateList.append(dev.state)
                sdp_master = True

        telescopeSetStateList = set(telescopeStateList)
        self._logger.info(f"Telescope state list is : {telescopeStateList}")
        if not sdp_master and not csp_master and not mccs_master:
            self._logger.info(
                "missing devices: %s=%s %s=%s %s=%s",
                self._component_manager.input_parameter.sdp_master_dev_name,
                sdp_master,
                self._component_manager.input_parameter.csp_master_dev_name,
                csp_master,
                self._component_manager.input_parameter.mccs_master_dev_name,
                mccs_master,
            )
            return DevState.UNKNOWN
        elif telescopeSetStateList == set([DevState.ON]):
            return DevState.ON
        elif telescopeSetStateList == set([DevState.OFF]):
            return DevState.OFF
        elif DevState.INIT in telescopeSetStateList:
            return DevState.INIT
        elif DevState.FAULT in telescopeSetStateList:
            return DevState.FAULT
        elif DevState.STANDBY in telescopeSetStateList:
            return DevState.STANDBY
        else:
            return DevState.UNKNOWN


class HealthStateAggregatorMid(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):
        # import debugpy; debugpy.debug_this_thread()
        healthStateList = []
        subarray_count = 0
        dish_count = 0
        csp_master = False
        sdp_master = False
        # get states of CspMaster, SdpMaster and DishMaster devices
        # what if one of them is not working (i.e. faulty flag)? i.e. Csp, Sdp or dishes
        # number of dishes is also variable
        for dev in self._component_manager.checked_devices:
            name = dev.dev_name.lower()
            if dev.unresponsive:
                continue
            elif (
                name
                == self._component_manager.input_parameter.csp_master_dev_name
            ):
                healthStateList.append(dev.health_state)
                csp_master = True
            elif (
                name
                == self._component_manager.input_parameter.sdp_master_dev_name
            ):
                healthStateList.append(dev.health_state)
                sdp_master = True
            elif (
                name
                in self._component_manager.input_parameter.subarray_dev_names
            ):
                healthStateList.append(dev.health_state)
                subarray_count += 1
            elif (
                name in self._component_manager.input_parameter.dish_dev_names
            ):
                healthStateList.append(dev.health_state)
                dish_count += 1

        healthStateSetList = set(healthStateList)
        if not sdp_master and not csp_master:
            return HealthState.UNKNOWN
        elif subarray_count == 0:
            return HealthState.UNKNOWN
        elif dish_count == 0:
            return HealthState.UNKNOWN
        elif healthStateSetList == set([HealthState.OK]):
            return HealthState.OK
        elif HealthState.FAILED in healthStateSetList:
            return HealthState.FAILED
        elif HealthState.DEGRADED in healthStateSetList:
            return HealthState.DEGRADED
        else:
            return HealthState.UNKNOWN


class HealthStateAggregatorLow(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):
        # import debugpy; debugpy.debug_this_thread()
        healthStateList = []
        subarray_count = 0
        csp_master = False
        sdp_master = False
        mccs_master = False
        # get health states of sdp, csp and mccs master devices
        for dev in self._component_manager.checked_devices:
            name = dev.dev_name.lower()
            if dev.unresponsive:
                continue
            elif (
                name
                == self._component_manager.input_parameter.csp_master_dev_name
            ):
                healthStateList.append(dev.health_state)
                csp_master = True
            elif (
                name
                == self._component_manager.input_parameter.sdp_master_dev_name
            ):
                healthStateList.append(dev.health_state)
                sdp_master = True
            elif (
                name
                in self._component_manager.input_parameter.subarray_dev_names
            ):
                healthStateList.append(dev.health_state)
                subarray_count += 1
            elif (
                name
                in self._component_manager.input_parameter.mccs_master_dev_name
            ):
                healthStateList.append(dev.health_state)
                mccs_master = True

        healthStateSetList = set(healthStateList)
        self._logger.info("Health state list : %s", healthStateList)
        if subarray_count == 0:
            return HealthState.UNKNOWN
        elif not sdp_master and not csp_master and not mccs_master:
            return HealthState.UNKNOWN
        elif healthStateSetList == set([HealthState.OK]):
            return HealthState.OK
        elif HealthState.FAILED in healthStateSetList:
            return HealthState.FAILED
        elif HealthState.DEGRADED in healthStateSetList:
            return HealthState.DEGRADED
        else:
            return HealthState.UNKNOWN


class TMCOpStateAggregator(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):
        tmcStateList = []
        # get states of all TM devices
        # what if one of them is not working? i.e. tm subarray
        # number of devices is also variable, how to handle that number
        for dev in self._component_manager.checked_devices:
            name = dev.dev_name.lower()
            if "tm" in name:
                if dev.unresponsive:
                    continue
                tmcStateList.append(dev.state)

        tmcSetStateList = set(tmcStateList)
        if tmcSetStateList == set([DevState.ON]):
            return DevState.ON
        elif tmcSetStateList == set([DevState.OFF]):
            #  Untill all TMC devices are refactored, devices report Off state.
            return DevState.OFF
        elif DevState.INIT in tmcSetStateList:
            return DevState.INIT
        elif DevState.FAULT in tmcSetStateList:
            return DevState.FAULT
        else:
            return DevState.UNKNOWN


class TelescopeAvailabilityAggregatorMid(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)
        self.logger = logger

    def aggregate(self):
        telescope_availability = (
            self._component_manager.get_telescope_availability()
        )
        for dev in self._component_manager.checked_devices:
            if "tm_subarray_node" in dev.dev_name:
                if dev.unresponsive:
                    telescope_availability["tmc_subarrays"][
                        dev.dev_name
                    ] = False
                else:
                    telescope_availability["tmc_subarrays"][
                        dev.dev_name
                    ] = self._component_manager.subarray_availability[
                        dev.dev_name
                    ]
            elif "tm_leaf_node/csp_master" in dev.dev_name:
                if dev.unresponsive:
                    telescope_availability["csp_master_leaf_node"] = False
                else:
                    telescope_availability[
                        "csp_master_leaf_node"
                    ] = self._component_manager.csp_mln_availability

            elif "tm_leaf_node/sdp_master" in dev.dev_name:
                if dev.unresponsive:
                    telescope_availability["sdp_master_leaf_node"] = False
                else:
                    telescope_availability[
                        "sdp_master_leaf_node"
                    ] = self._component_manager.sdp_mln_availability

            self._component_manager.set_telescope_availability = (
                telescope_availability
            )


class TelescopeAvailabilityAggregatorLow(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)
        self.logger = logger

    def aggregate(self):
        telescope_availability = (
            self._component_manager.get_telescope_availability()
        )
        for dev in self._component_manager.checked_devices:
            if "tm_subarray_node" in dev.dev_name:
                if dev.unresponsive:
                    telescope_availability["tmc_subarrays"][
                        dev.dev_name
                    ] = False
                else:
                    telescope_availability["tmc_subarrays"][
                        dev.dev_name
                    ] = self._component_manager.subarray_availability[
                        dev.dev_name
                    ]
            elif "tm_leaf_node/csp_master" in dev.dev_name:
                if dev.unresponsive:
                    telescope_availability["csp_master_leaf_node"] = False
                else:
                    telescope_availability[
                        "csp_master_leaf_node"
                    ] = self._component_manager.csp_mln_availability

            elif "tm_leaf_node/sdp_master" in dev.dev_name:
                if dev.unresponsive:
                    telescope_availability["sdp_master_leaf_node"] = False
                else:
                    telescope_availability[
                        "sdp_master_leaf_node"
                    ] = self._component_manager.sdp_mln_availability

            elif MCCS_MLN_SUFIX in dev.dev_name:
                if dev.unresponsive:
                    telescope_availability["mccs_master_leaf_node"] = False
                else:
                    telescope_availability[
                        "mccs_master_leaf_node"
                    ] = self._component_manager.mccs_mln_availability

            self._component_manager.set_telescope_availability = (
                telescope_availability
            )


class LoadDishCfgCommandResultAggregator:
    """This Class Aggregate LoadDishCfg command results
    from Csp Master Leaf Nodes and Dish Leaf Nodes
    """

    def __init__(self, cm, logger) -> None:
        """
        :param cm: Central Node Component Manager
        :param type: component manager
        :param logger: Logger
        """
        self._component_manager = cm
        self.logger = logger

    def _get_result_codes_and_failed_msg(self) -> tuple:
        """Get Result codes list and failed message list from command result"""
        result_codes = []
        failed_messages = []
        for (
            dev_name,
            result_code_message_list,
        ) in self._component_manager.result_codes_mapping.items():
            result_codes.append(int(result_code_message_list[0]))
            if int(result_code_message_list[0]) == ResultCode.FAILED:
                failed_message = f"{dev_name}: {result_code_message_list[1]}"
                failed_messages.append(failed_message)
        return result_codes, failed_messages

    def aggregate(self) -> tuple:
        """Aggregate the results and return Final Result code
        :retrun: result code and message
        :return type: tuple
        """
        result_code = ""
        message = ""
        self.logger.info(
            "Aggregating result for longRunningCommandResult attribute with values %s",
            self._component_manager.result_codes_mapping.values(),
        )
        result_codes, failed_messages = self._get_result_codes_and_failed_msg()
        self.logger.info(
            "Result codes are %s and failed messages are %s",
            result_codes,
            failed_messages,
        )

        if ResultCode.FAILED in result_codes:
            result_code = ResultCode.FAILED
            failed_message_join = " ".join(failed_messages)
            message = f"Command failed on device {failed_message_join}"

        result_codes_set = set(result_codes)
        if result_codes_set == set([ResultCode.OK]):
            result_code = ResultCode.OK
        self.logger.info(
            "Returning result code %s and message %s", result_code, message
        )
        return result_code, message

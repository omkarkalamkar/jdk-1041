from ska_control_model import HealthState
from ska_tmc_common.aggregators import Aggregator
from ska_tmc_common.enum import DishMode
from tango import DevState


class TelescopeStateAggregatorMid(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):
        # import debugpy; debugpy.debug_this_thread()
        telescopeStateList = []
        dishmodeset = set()
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
                dishmodeset.add(dev.dishMode)
                dish_count += 1
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
        self._logger.info(
            "telescopeSetStateList : %s , dishmodeset : %s ",
            telescopeSetStateList,
            dishmodeset,
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
        elif telescopeSetStateList == {DevState.ON} and dishmodeset == {
            DishMode.STANDBY_FP
        }:
            return DevState.ON
        elif telescopeSetStateList == {DevState.OFF} and dishmodeset == {
            DishMode.STANDBY_LP
        }:
            return DevState.OFF
        elif DevState.INIT in telescopeSetStateList:
            return DevState.INIT
        elif DevState.FAULT in telescopeSetStateList:
            return DevState.FAULT
        elif (
            DevState.STANDBY in telescopeSetStateList
            or DishMode.STANDBY_LP in dishmodeset
        ):
            return DevState.STANDBY
        else:
            return DevState.UNKNOWN


class TelescopeStateAggregatorLow(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):

        telescopeStateList = []
        #  mccs_master = False
        csp_master = False
        sdp_master = False

        for dev in self._component_manager.checked_devices:
            name = dev.dev_name.lower()
            if dev.unresponsive:
                continue
            # TODO: Enable this block when MCCS is integrated.
            # elif (
            #     name
            #     == self._component_manager.input_parameter.mccs_master_dev_name
            # ):
            #     telescopeStateList.append(dev.state)
            #     mccs_master = True
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
        if not sdp_master and not csp_master:
            self._logger.info(
                "missing devices: %s=%s %s=%s",
                self._component_manager.input_parameter.sdp_master_dev_name,
                sdp_master,
                self._component_manager.input_parameter.csp_master_dev_name,
                csp_master,
            )
            return DevState.UNKNOWN
        # if not mccs_master:
        #     return DevState.UNKNOWN
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
        # mccs_master = False
        # get health states of sdp and csp master devices
        # TODO: Add MCCS once it is integrated
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
            # elif (
            #     name
            #     in self._component_manager.input_parameter.mccs_master_dev_name
            # ):
            #     healthStateList.append(dev.health_state)
            #     mccs_master = True

        healthStateSetList = set(healthStateList)
        self._logger.info("Health state list : %s", healthStateList)
        # if not mccs_master:
        #     return HealthState.UNKNOWN
        if subarray_count == 0:
            return HealthState.UNKNOWN
        elif not sdp_master and not csp_master:
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

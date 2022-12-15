from ska_tango_base.control_model import HealthState
from ska_tmc_common.aggregators import Aggregator
from tango import DevState


class TelescopeStateAggregatorMid(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):
        # import debugpy; debugpy.debug_this_thread()
        telescopeStateList = []
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
                telescopeStateList.append(dev.state)
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
            # self._logger.info(
            #     "telescopeSetStateList: %s", telescopeSetStateList
            # )
            return DevState.UNKNOWN


class TelescopeStateAggregatorLow(Aggregator):
    def __init__(self, cm, logger) -> None:
        super().__init__(cm, logger)

    def aggregate(self):
        # Currently there is only MCCS in the Low. But this algorithm leaves a
        #  place to consider CSP and SDP states when they will be integrated.
        telescopeStateList = []
        mccs_master = False

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

        if not sdp_master and not csp_master:
            self._logger.info(
                "missing devices: %s=%s %s=%s",
                self._component_manager.input_parameter.sdp_master_dev_name,
                sdp_master,
                self._component_manager.input_parameter.csp_master_dev_name,
                csp_master,
            )
            return DevState.UNKNOWN
        if not mccs_master:
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
                in self._component_manager.input_parameter.tm_subarray_dev_names
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
        mccs_master = False
        # get health states of MCCS Master devices
        for dev in self._component_manager.checked_devices:
            name = dev.dev_name.lower()
            if dev.unresponsive:
                continue
            elif (
                name
                == self._component_manager.input_parameter.csp_master_dev_name
            ):
                healthStateList.append(dev.healthState)
                csp_master = True
            elif (
                name
                == self._component_manager.input_parameter.sdp_master_dev_name
            ):
                healthStateList.append(dev.healthState)
                sdp_master = True
            elif (
                name
                in self._component_manager.input_parameter.tm_subarray_dev_names
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
        if not mccs_master:
            return HealthState.UNKNOWN
        elif subarray_count == 0:
            return HealthState.UNKNOWN
        elif not sdp_master and not csp_master == 0:
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
        tmStateList = []
        # get states of all TM devices
        # what if one of them is not working? i.e. tm subarray
        # number of devices is also variable, how to handle that number
        for dev in self._component_manager.checked_devices:
            name = dev.dev_name.lower()
            if "tm" in name:
                if dev.unresponsive:
                    continue
                tmStateList.append(dev.state)

        tmSetStateList = set(tmStateList)
        if tmSetStateList == set([DevState.ON]):
            return DevState.ON
        elif tmSetStateList == set([DevState.OFF]):
            #  Untill all TMC devices are refactored, devices report Off state.
            return DevState.OFF
        elif DevState.INIT in tmSetStateList:
            return DevState.INIT
        elif DevState.FAULT in tmSetStateList:
            return DevState.FAULT
        else:
            return DevState.UNKNOWN

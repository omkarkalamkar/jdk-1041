from ska_tango_base.control_model import HealthState
from tango import DevState


class Aggregator:
    def __init__(self, cm, logger) -> None:
        self._component_manager = cm
        self._logger = logger

    def aggregate(self):
        raise NotImplementedError("To be defined in the lower level classes")


class TelescopeStateAggragator(Aggregator):
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
            if "leaf" in name:
                continue
            elif dev.faulty:
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


class HealthStateAggragator(Aggregator):
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
            if "leaf" in name:
                continue
            elif dev.faulty:
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
                healthStateList.append(dev.healthState)
                subarray_count += 1
            elif (
                name in self._component_manager.input_parameter.dish_dev_names
            ):
                healthStateList.append(dev.healthState)
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


class TMCOpStateAggragator(Aggregator):
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
                tmStateList.append(dev.state)

        tmSetStateList = set(tmStateList)
        if tmSetStateList == set([DevState.ON]):
            return DevState.ON
        elif tmSetStateList == set([DevState.OFF]):
            #  Untill all TMC devices are refactored, devices report Off state.
            raise Exception("OFF State not allowed")
        elif DevState.INIT in tmSetStateList:
            return DevState.INIT
        elif DevState.FAULT in tmSetStateList:
            return DevState.FAULT
        else:
            return DevState.UNKNOWN

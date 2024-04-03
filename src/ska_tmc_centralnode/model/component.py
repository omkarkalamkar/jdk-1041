""" Component class for central node"""
import json
import threading
from typing import List, Optional

import tango
from ska_control_model import HealthState
from ska_tmc_common.device_info import DeviceInfo
from ska_tmc_common.tmc_component_manager import TmcComponent
from tango import DevState

from ska_tmc_centralnode.model.enum import ModesAvailability


def dev_state_2_str(value: DevState) -> str:
    """Converts DevState to strings"""
    dev_state_map = {
        DevState.ON: "DevState.ON",
        DevState.OFF: "DevState.OFF",
        DevState.CLOSE: "DevState.CLOSE",
        DevState.OPEN: "DevState.OPEN",
        DevState.INSERT: "DevState.INSERT",
        DevState.EXTRACT: "DevState.EXTRACT",
        DevState.MOVING: "DevState.MOVING",
        DevState.STANDBY: "DevState.STANDBY",
        DevState.FAULT: "DevState.FAULT",
        DevState.INIT: "DevState.INIT",
        DevState.RUNNING: "DevState.RUNNING",
        DevState.ALARM: "DevState.ALARM",
        DevState.DISABLE: "DevState.DISABLE",
    }
    return dev_state_map.get(value, "DevState.UNKNOWN")


class CentralComponent(TmcComponent):
    """
    A component class for Central Node

    It supports:

    * Maintaining a connection to its component

    * Monitoring its component
    """

    def __init__(self, logger):
        super().__init__(logger)

        self._devices = []
        self.logger = logger
        self._telescope_state = DevState.UNKNOWN
        self._tmc_op_state = DevState.UNKNOWN
        self._telescope_health_state = HealthState.UNKNOWN
        # _health_state is never changing. Setter not implemented
        self._health_state = HealthState.OK
        self._vlbi = ModesAvailability.not_available
        self._imaging = ModesAvailability.not_available
        self._pss = ModesAvailability.not_available
        self._pst = ModesAvailability.not_available
        self._update_device_callback = None
        self._update_telescope_state_callback = None
        self._update_telescope_health_state_callback = None
        self._update_tmc_op_state_callback = None
        self._telescope_availability_callback = None
        self._update_imaging_callback = None
        self._telescope_availability = {
            "tmc_subarrays": {},
            "csp_master_leaf_node": False,
            "sdp_master_leaf_node": False,
            "mccs_master_leaf_node": False,
        }
        self.lock = threading.Lock()
        self._desired_telescope_state = DevState.ON

    def set_op_callbacks(
        self,
        _update_device_callback=None,
        _update_telescope_state_callback=None,
        _update_telescope_health_state_callback=None,
        _update_tmc_op_state_callback=None,
        _update_imaging_callback=None,
        _telescope_availability_callback=None,
    ):
        """Sets Op state callback"""
        self._update_device_callback = _update_device_callback
        self._update_telescope_state_callback = (
            _update_telescope_state_callback
        )
        self._update_telescope_health_state_callback = (
            _update_telescope_health_state_callback
        )
        self._update_tmc_op_state_callback = _update_tmc_op_state_callback
        self._update_imaging_callback = _update_imaging_callback
        self._telescope_availability_callback = (
            _telescope_availability_callback
        )

    def _invoke_device_callback(self, dev_info: DeviceInfo) -> None:
        """invokes device callback"""
        if self._update_device_callback is not None:
            self._update_device_callback(dev_info)

    def _invoke_telescope_state_callback(self) -> None:
        """invokes telescope state callback"""
        if self._update_telescope_state_callback is not None:
            self._update_telescope_state_callback(self.telescope_state)

    def _invoke_telescope_health_state_callback(self) -> None:
        """invokes telescope health state callback"""
        if self._update_telescope_health_state_callback is not None:
            self._update_telescope_health_state_callback(
                self.telescope_health_state
            )

    def _invoke_tmc_op_state_callback(self) -> None:
        """Invokes tmc op_state callback"""
        if self._update_tmc_op_state_callback is not None:
            self._update_tmc_op_state_callback(self.tmc_op_state)

    def _invoke_imaging_callback(self) -> None:
        """Invokes imaging callback"""
        if self._update_imaging_callback is not None:
            self._update_imaging_callback(self.imaging)

    def _invoke_telescope_availability_callback(self) -> None:
        """Invokes telescope availablity callback"""
        if self._telescope_availability_callback is not None:
            self._telescope_availability_callback(self.telescope_availability)

    @property
    def desired_telescope_state(self) -> tango.DevState:
        """
        Return desired telescope state

        :return: desired telescope state
        :rtype: DevState
        """
        return self._desired_telescope_state

    @desired_telescope_state.setter
    def desired_telescope_state(self, value: tango.DevState) -> None:
        """
        Set desired telescope state

        :param value: desired telescope state
        :type value: DevState
        """
        if not value == self._desired_telescope_state:
            self._desired_telescope_state = value

    @property
    def devices(self) -> List[DevState]:
        """
        Return the monitored devices.

        :return: the monitored devices
        :rtype: DeviceInfo[]
        """
        return self._devices

    def get_device(self, device_name: str) -> Optional[DeviceInfo]:
        """
        Return the monitored device info by name.

        :param dev_name: name of the device
        :return: the monitored device info
        :rtype: DeviceInfo
        """
        for dev_info in self.devices:
            if device_name in dev_info.dev_name:
                return dev_info
        return None

    def remove_device(self, dev_name: str) -> None:
        """
        Remove a device from the list

        :param dev_name: name of the device
        """
        for dev_info in self.devices:
            if dev_info.dev_name == dev_name:
                self.devices.remove(dev_info)

    def update_device(self, dev_info: DeviceInfo) -> None:
        """
        Update (or add if missing) Device Information into the list of the
        component.

        :param dev_info: a DeviceInfo object
        """
        if dev_info not in self._devices:
            self._devices.append(dev_info)
        else:
            index = self._devices.index(dev_info)
            self._devices[index] = dev_info
        self.logger.info("Devices added are: %s", self.devices)
        self._invoke_device_callback(dev_info)

    def update_device_exception(
        self, device_info: DeviceInfo, exception: str
    ) -> None:
        """
        Update (or add if missing) Device Information into the list of the
          component.

        :param dev_info: a DeviceInfo object
        """
        if device_info not in self._devices:
            device_info.update_unresponsive(True, exception)
            self._devices.append(device_info)
            self._invoke_device_callback(device_info)
        else:
            index = self._devices.index(device_info)
            intdev_info = self._devices[index]
            intdev_info.state = DevState.UNKNOWN
            intdev_info.update_unresponsive(True, exception)
            self._invoke_device_callback(intdev_info)

    @property
    def telescope_state(self) -> tango.DevState:
        """
        Return the telescope state

        :return: the telescope state
        :rtype: DevState
        """
        return self._telescope_state

    @telescope_state.setter
    def telescope_state(self, value: tango.DevState) -> None:
        """
        Set telescope state

        :param value: the new telescope state
        :type value: DevState
        """
        if self._telescope_state != value:
            self._telescope_state = value
            self._invoke_telescope_state_callback()

    @property
    def telescope_availability(self) -> str:
        """
        Returns the telescope availability

        :return: the telescope availability
        :rtype: DevVarStringArray
        """
        return self._telescope_availability

    @telescope_availability.setter
    def telescope_availability(self, value: tango.DevState) -> None:
        """
        Set telescope availability

        :param value: the new telescope availability
        :type value: DevState
        """
        if self._telescope_availability != value:
            self._telescope_availability = value
            self._invoke_telescope_availability_callback()

    @property
    def telescope_health_state(self) -> HealthState:
        """
        Return the telescope health state

        :return: the telescope health state
        :rtype: HealthState
        """
        return self._telescope_health_state

    @telescope_health_state.setter
    def telescope_health_state(self, value: HealthState) -> None:
        """
        Set telescope health state

        :param value: the new telescope health state
        :type value: HealthState
        """
        if self._telescope_health_state != value:
            self._telescope_health_state = value
            self._invoke_telescope_health_state_callback()

    @property
    def tmc_op_state(self) -> tango.DevState:
        """
        Return the TMC operational State

        :return: the TMC operational State
        :rtype: DevState
        """
        return self._tmc_op_state

    @tmc_op_state.setter
    def tmc_op_state(self, value: tango.DevState) -> None:
        """
        Set the TMC operational State

        :param value: the TMC operational State
        :type value: DevState
        """
        if self._tmc_op_state != value:
            self._tmc_op_state = value
            self._invoke_tmc_op_state_callback()

    @property
    def vlbi(self) -> ModesAvailability:
        """
        Return vlbi ModesAvailability

        :return: vlbi ModesAvailability
        :rtype: ModesAvailability
        """
        return self._vlbi

    @vlbi.setter
    def vlbi(self, value: ModesAvailability) -> None:
        """
        Set vlbi ModesAvailability

        :param value: vlbi ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            self._vlbi = value

    @property
    def imaging(self) -> ModesAvailability:
        """
        Return vlbi ModesAvailability

        :return: vlbi ModesAvailability
        :rtype: ModesAvailability
        """
        return self._imaging

    @imaging.setter
    def imaging(self, value: ModesAvailability) -> None:
        """
        Set vlbi ModesAvailability

        :param value: vlbi ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            if self._imaging != value:
                self._imaging = value
                self._invoke_imaging_callback()

    @property
    def pss(self) -> ModesAvailability:
        """
        Return pss ModesAvailability

        :return: pss ModesAvailability
        :rtype: ModesAvailability
        """
        return self._pss

    @pss.setter
    def pss(self, value: ModesAvailability) -> None:
        """
        Set pss ModesAvailability

        :param value: pss ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            self._pss = value

    @property
    def pst(self) -> ModesAvailability:
        """
        Return pss ModesAvailability

        :return: pss ModesAvailability
        :rtype: ModesAvailability
        """
        return self._pst

    @pst.setter
    def pst(self, value: ModesAvailability) -> None:
        """
        Set pss ModesAvailability

        :param value: pss ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            self._pst = value

    def to_json(self) -> str:
        """Converts dictionary to json
        :return: Json string
        :rtype: str
        """
        return json.dumps(self.to_dict())

    def to_dict(self):
        """Converts devinfo to python dictionary"""
        devices = []
        for dev in self.devices:
            devices.append(dev.to_dict())
        result = {
            "telescope_state": dev_state_2_str(
                DevState(self._telescope_state)
            ),
            "tmc_op_state": dev_state_2_str(DevState(self._tmc_op_state)),
            "telescope_health_state": str(
                HealthState(self._telescope_health_state)
            ),
            "devices": devices,
        }

        return result


class MCCSDeviceInfo(DeviceInfo):
    """Devicesinfo Class for MCCS Devices"""

    def __init__(self, dev_name, _unresponsive=False):
        super().__init__(dev_name, _unresponsive)
        self.resources = {}

    def from_dev_info(self, dev_info: DeviceInfo) -> None:
        """Device info to MCCSDeviceInfo"""
        super().from_dev_info(dev_info)
        if isinstance(dev_info, MCCSDeviceInfo):
            self.resources = dev_info.resources

    def __eq__(self, other) -> bool:
        """__eq__ method for MCCS DeviceInfo"""
        if isinstance(other, (MCCSDeviceInfo, DeviceInfo)):
            return self.dev_name == other.dev_name
        return False

    def to_json(self):
        """
        This method Converts DevInfo to Json
        :return: Json string
        :rtype: str"""
        return json.dumps(self.to_dict())

    def to_dict(self):
        """This method Converts Devinfo to Dict
        :return: resources json
        :rtype: dict
        """
        super_dict = super().to_dict()
        super_dict["resources"] = self.resources
        return super_dict

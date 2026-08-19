"""Component class for central node"""

import json
import threading
from collections import defaultdict
from typing import List, Optional

import tango
from ska_control_model import HealthState
from ska_tango_base.software_bus import SharingObserver, Signal
from ska_tmc_common.device_info import DeviceInfo
from ska_tmc_common.v2.tmc_component_manager import TmcComponent
from tango import DevState

from ska_tmc_centralnode.model.enum import ModesAvailability


def dev_state_2_str(value: DevState) -> str:
    """
    Converts DevState to strings

    Args:
        value (DevState): DevState

    Returns:
        str: DevState converted to string

    """
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


class CentralComponent(SharingObserver, TmcComponent):
    """
    A component class for Central Node

    It supports:

    * Maintaining a connection to its component

    * Monitoring its component
    """

    _desired_telescope_state: Signal[tango.DevState] = Signal[tango.DevState](
        stored=True, initial_value=tango.DevState.ON
    )
    _telescope_state: Signal[tango.DevState] = Signal[tango.DevState](
        stored=True, initial_value=tango.DevState.UNKNOWN
    )
    _tmc_op_state: Signal[tango.DevState] = Signal[str](
        stored=True, initial_value=tango.DevState.UNKNOWN
    )
    _telescope_availability: Signal[dict] = Signal[dict](
        stored=True, initial_value={"tmc_subarrays": defaultdict(bool)}
    )
    _telescope_health_state: Signal[HealthState] = Signal[HealthState](
        stored=True, initial_value=HealthState.UNKNOWN
    )
    _last_device_info_changed: Signal[str] = Signal[str](stored=True)
    _imaging: Signal[ModesAvailability] = Signal[ModesAvailability](
        stored=True, initial_value=ModesAvailability.NOT_AVAILABLE
    )

    def __init__(self, logger):
        super().__init__(logger)

        self._devices = []
        self.logger = logger
        # _health_state is never changing. Setter not implemented
        self._health_state = HealthState.OK
        self._vlbi = ModesAvailability.NOT_AVAILABLE
        self._pss = ModesAvailability.NOT_AVAILABLE
        self._pst = ModesAvailability.NOT_AVAILABLE
        self.lock = threading.Lock()
        self.rlock = threading._RLock()

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
    def devices(self) -> List[DeviceInfo]:
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
        self.last_device_info_changed = dev_info

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
            self.last_device_info_changed = device_info
        else:
            index = self._devices.index(device_info)
            intdev_info = self._devices[index]
            intdev_info.state = DevState.UNKNOWN
            intdev_info.update_unresponsive(True, exception)
            self.last_device_info_changed = device_info

    @property
    def last_device_info_changed(self) -> str:
        """Provides last device information that has been changed."""
        return self._last_device_info_changed

    @last_device_info_changed.setter
    def last_device_info_changed(self, dev_info: DeviceInfo) -> None:
        """Updates the last device information changed attribute.

        :param dev_info: Device Information.
        :type dev_info: DeviceInfo
        """
        dev_info_str = dev_info.to_json()
        self._last_device_info_changed = dev_info_str

    @property
    def telescope_state(self) -> tango.DevState:
        """
        Return the telescope state

        :return: the telescope state
        :rtype: DevState
        """
        with self.rlock:
            return self._telescope_state

    @telescope_state.setter
    def telescope_state(self, value: tango.DevState) -> None:
        """
        Set telescope state

        :param value: the new telescope state
        :type value: DevState
        """
        with self.rlock:
            if self._telescope_state != value:
                self._telescope_state = value

    @property
    def telescope_availability(self) -> dict:
        """
        Returns the telescope availability

        :return: the telescope availability
        :rtype: DevVarStringArray
        """
        with self.rlock:
            return self._telescope_availability

    @telescope_availability.setter
    def telescope_availability(self, value: dict) -> None:
        """
        Set telescope availability

        :param value: the new telescope availability
        :type value: DevState
        """
        with self.rlock:
            if self._telescope_availability != value:
                self._telescope_availability = value

    @property
    def telescope_health_state(self) -> HealthState:
        """
        Return the telescope health state

        :return: the telescope health state
        :rtype: HealthState
        """
        with self.rlock:
            return self._telescope_health_state

    @telescope_health_state.setter
    def telescope_health_state(self, value: HealthState) -> None:
        """
        Set telescope health state

        :param value: the new telescope health state
        :type value: HealthState
        """
        with self.rlock:
            if self._telescope_health_state != value:
                self._telescope_health_state = value

    @property
    def tmc_op_state(self) -> tango.DevState:
        """
        Return the TMC operational State

        :return: the TMC operational State
        :rtype: DevState
        """
        with self.rlock:
            return self._tmc_op_state

    @tmc_op_state.setter
    def tmc_op_state(self, value: tango.DevState) -> None:
        """
        Set the TMC operational State

        :param value: the TMC operational State
        :type value: DevState
        """
        with self.rlock:
            if self._tmc_op_state != value:
                self._tmc_op_state = value

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
        """
        Converts dictionary to json

        Returns:
            str: Json string

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

    def to_json(self) -> str:
        """
        This method Converts DevInfo to Json

        Returns:
            str: Json string

        """
        return json.dumps(self.to_dict())

    def to_dict(self) -> dict:
        """
        This method Converts Devinfo to Dict

        Returns:
            dict: resources json

        """
        super_dict = super().to_dict()
        super_dict["resources"] = self.resources
        return super_dict

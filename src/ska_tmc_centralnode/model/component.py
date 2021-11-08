import json
import threading

from ska_tango_base.control_model import HealthState, ObsState
from tango import DevState

from ska_tmc_centralnode.model.enum import ModesAvailability


def dev_state_2_str(value):
    if value == DevState.ON:
        return "DevState.ON"
    elif value == DevState.OFF:
        return "DevState.OFF"
    elif value == DevState.CLOSE:
        return "DevState.CLOSE"
    elif value == DevState.OPEN:
        return "DevState.OPEN"
    elif value == DevState.INSERT:
        return "DevState.INSERT"
    elif value == DevState.EXTRACT:
        return "DevState.EXTRACT"
    elif value == DevState.MOVING:
        return "DevState.MOVING"
    elif value == DevState.STANDBY:
        return "DevState.STANDBY"
    elif value == DevState.FAULT:
        return "DevState.FAULT"
    elif value == DevState.INIT:
        return "DevState.INIT"
    elif value == DevState.RUNNING:
        return "DevState.RUNNING"
    elif value == DevState.ALARM:
        return "DevState.ALARM"
    elif value == DevState.DISABLE:
        return "DevState.DISABLE"
    else:
        return "DevState.UNKNOWN"


class Component:
    """
    A component class for Central Node

    It supports:

    * Maintaining a connection to its component

    * Monitoring its component
    """

    def __init__(self, logger):
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
        self._update_subarray_health_state_callback = None
        self.lock = threading.Lock()
        self._desired_telescope_state = DevState.ON

    def set_op_callbacks(
        self,
        _update_device_callback=None,
        _update_telescope_state_callback=None,
        _update_telescope_health_state_callback=None,
        _update_tmc_op_state_callback=None,
        _update_subarray_health_state_callback=None,
        _update_imaging_callback=None,
    ):
        self._update_device_callback = _update_device_callback
        self._update_telescope_state_callback = (
            _update_telescope_state_callback
        )
        self._update_telescope_health_state_callback = (
            _update_telescope_health_state_callback
        )
        self._update_tmc_op_state_callback = _update_tmc_op_state_callback
        self._update_subarray_health_state_callback = (
            _update_subarray_health_state_callback
        )
        self._update_imaging_callback = _update_imaging_callback

    def _invoke_device_callback(self, devInfo):
        if self._update_device_callback is not None:
            self._update_device_callback(devInfo)

    def _invoke_telescope_state_callback(self):
        if self._update_telescope_state_callback is not None:
            self._update_telescope_state_callback(self.telescope_state)

    def _invoke_telescope_health_state_callback(self):
        if self._update_telescope_health_state_callback is not None:
            self._update_telescope_health_state_callback(
                self.telescope_health_state
            )

    def _invoke_tmc_op_state_callback(self):
        if self._update_tmc_op_state_callback is not None:
            self._update_tmc_op_state_callback(self.tmc_op_state)

    def _invoke_subarray_health_state_callback(self, devInfo):
        if self._update_subarray_health_state_callback is not None:
            self._update_subarray_health_state_callback(devInfo)

    def _invoke_imaging_callback(self):
        if self._update_imaging_callback is not None:
            self._update_imaging_callback(self.imaging)

    @property
    def desired_telescope_state(self):
        """
        Return desired telescope state

        :return: desired telescope state
        :rtype: DevState
        """
        return self._desired_telescope_state

    @desired_telescope_state.setter
    def desired_telescope_state(self, value):
        """
        Set desired telescope state

        :param value: desired telescope state
        :type value: DevState
        """
        if not value == self._desired_telescope_state:
            self._desired_telescope_state = value

    @property
    def devices(self):
        """
        Return the monitored devices.

        :return: the monitored devices
        :rtype: DeviceInfo[]
        """
        return self._devices

    def get_device(self, dev_name):
        """
        Return the monitored device info by name.

        :param dev_name: name of the device
        :return: the monitored device info
        :rtype: DeviceInfo
        """
        for devInfo in self.devices:
            if devInfo.dev_name == dev_name:
                return devInfo
        return None

    def remove_device(self, dev_name):
        """
        Remove a device from the list

        :param dev_name: name of the device
        """
        for devInfo in self.devices:
            if devInfo.dev_name == dev_name:
                self.devices.remove(devInfo)

    def update_device(self, devInfo):
        """
        Update (or add if missing) Device Information into the list of the component.

        :param devInfo: a DeviceInfo object
        """
        if devInfo not in self._devices:
            self._devices.append(devInfo)
        else:
            index = self._devices.index(devInfo)
            if isinstance(devInfo, SubArrayDeviceInfo):
                if devInfo.healthState != self._devices[index].healthState:
                    self._invoke_subarray_health_state_callback(devInfo)
            self._devices[index] = devInfo

        self._invoke_device_callback(devInfo)

    def update_device_exception(self, devInfo, exception):
        """
        Update (or add if missing) Device Information into the list of the component.

        :param devInfo: a DeviceInfo object
        """
        if devInfo not in self._devices:
            devInfo.update_unresponsive(True, exception)
            self._devices.append(devInfo)
            self._invoke_device_callback(devInfo)
        else:
            index = self._devices.index(devInfo)
            intDevInfo = self._devices[index]
            intDevInfo.state = DevState.UNKNOWN
            intDevInfo.update_unresponsive(True, exception)
            self._invoke_device_callback(intDevInfo)

    @property
    def telescope_state(self):
        """
        Return the telescope state

        :return: the telescope state
        :rtype: DevState
        """
        return self._telescope_state

    @telescope_state.setter
    def telescope_state(self, value):
        """
        Set telescope state

        :param value: the new telescope state
        :type value: DevState
        """
        if self._telescope_state != value:
            self._telescope_state = value
            self._invoke_telescope_state_callback()

    @property
    def telescope_health_state(self):
        """
        Return the telescope health state

        :return: the telescope health state
        :rtype: HealthState
        """
        return self._telescope_health_state

    @telescope_health_state.setter
    def telescope_health_state(self, value):
        """
        Set telescope health state

        :param value: the new telescope health state
        :type value: HealthState
        """
        # if isinstance(value, HealthState):
        if self._telescope_health_state != value:
            self._telescope_health_state = value
            self._invoke_telescope_health_state_callback()

    @property
    def tmc_op_state(self):
        """
        Return the TMC operational State

        :return: the TMC operational State
        :rtype: DevState
        """
        return self._tmc_op_state

    @tmc_op_state.setter
    def tmc_op_state(self, value):
        """
        Set the TMC operational State

        :param value: the TMC operational State
        :type value: DevState
        """
        if self._tmc_op_state != value:
            self._tmc_op_state = value
            self._invoke_tmc_op_state_callback()

    @property
    def vlbi(self):
        """
        Return vlbi ModesAvailability

        :return: vlbi ModesAvailability
        :rtype: ModesAvailability
        """
        return self._vlbi

    @vlbi.setter
    def vlbi(self, value):
        """
        Set vlbi ModesAvailability

        :param value: vlbi ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            self._vlbi = value

    @property
    def imaging(self):
        """
        Return vlbi ModesAvailability

        :return: vlbi ModesAvailability
        :rtype: ModesAvailability
        """
        return self._imaging

    @imaging.setter
    def imaging(self, value):
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
    def pss(self):
        """
        Return pss ModesAvailability

        :return: pss ModesAvailability
        :rtype: ModesAvailability
        """
        return self._pss

    @pss.setter
    def pss(self, value):
        """
        Set pss ModesAvailability

        :param value: pss ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            self._pss = value

    @property
    def pst(self):
        """
        Return pss ModesAvailability

        :return: pss ModesAvailability
        :rtype: ModesAvailability
        """
        return self._pst

    @pst.setter
    def pst(self, value):
        """
        Set pss ModesAvailability

        :param value: pss ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            self._pst = value

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
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


class DeviceInfo:
    def __init__(self, dev_name: str, _unresponsive=False):
        self.dev_name = dev_name
        self.state = DevState.UNKNOWN
        self.obsState = ObsState.EMPTY
        self.healthState = HealthState.UNKNOWN
        self.ping = -1
        self.last_event_arrived = None
        self.exception = None
        self._unresponsive = _unresponsive
        self.lock = threading.Lock()

    def from_dev_info(self, devInfo):
        self.dev_name = devInfo.dev_name
        self.state = devInfo.state
        self.healthState = devInfo.healthState
        self.ping = devInfo.ping
        self.last_event_arrived = devInfo.last_event_arrived
        self.lock = devInfo.lock

    def update_unresponsive(self, value, exception=None):
        """
        Set device unresponsive

        :param: value unresponsive boolean
        """
        self._unresponsive = value
        self.exception = exception
        if self._unresponsive:
            self.state = DevState.UNKNOWN
            self.obsState = ObsState.EMPTY
            self.healthState = HealthState.UNKNOWN
            self.ping = -1

    @property
    def unresponsive(self):
        """
        Return whether this device is currently unresponsive.

        :return: whether this device is faulting
        :rtype: bool
        """
        return self._unresponsive

    def __eq__(self, other):
        if isinstance(other, DeviceInfo):
            return self.dev_name == other.dev_name
        else:
            return False

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        result = {
            "dev_name": self.dev_name,
            "state": dev_state_2_str(DevState(self.state)),
            "obsState": str(ObsState(self.obsState)),
            "healthState": str(HealthState(self.healthState)),
            "ping": str(self.ping),
            "last_event_arrived": str(self.last_event_arrived),
            "unresponsive": str(self.unresponsive),
            "exception": str(self.exception),
        }
        return result


class SubArrayDeviceInfo(DeviceInfo):
    def __init__(self, dev_name, _unresponsive=False):
        super(SubArrayDeviceInfo, self).__init__(dev_name, _unresponsive)
        self.id = -1
        self.resources = []
        self.obsState = ObsState.EMPTY

    def from_dev_info(self, subarrayDevInfo):
        super().from_dev_info(subarrayDevInfo)
        if isinstance(subarrayDevInfo, SubArrayDeviceInfo):
            self.id = subarrayDevInfo.id
            self.resources = subarrayDevInfo.resources
            self.obsState = subarrayDevInfo.obsState

    def __eq__(self, other):
        if isinstance(other, SubArrayDeviceInfo) or isinstance(
            other, DeviceInfo
        ):
            return self.dev_name == other.dev_name
        else:
            return False

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        super_dict = super().to_dict()
        result = []
        if self.resources is not None:
            for res in self.resources:
                result.append(res)
            super_dict["resources"] = result
        super_dict["resources"] = result
        super_dict["id"] = self.id
        super_dict["obsState"] = str(ObsState(self.obsState))
        return super_dict


class MCCSDeviceInfo(DeviceInfo):
    def __init__(self, dev_name, _unresponsive=False):
        super(MCCSDeviceInfo, self).__init__(dev_name, _unresponsive)
        self.resources = {}

    def from_dev_info(self, mccsDevInfo):
        super().from_dev_info(mccsDevInfo)
        if isinstance(mccsDevInfo, MCCSDeviceInfo):
            self.resources = mccsDevInfo.resources

    def __eq__(self, other):
        if isinstance(other, MCCSDeviceInfo) or isinstance(other, DeviceInfo):
            return self.dev_name == other.dev_name
        else:
            return False

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        super_dict = super().to_dict()
        super_dict["resources"] = self.resources
        return super_dict

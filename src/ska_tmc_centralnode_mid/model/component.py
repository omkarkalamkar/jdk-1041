from ska_tango_base.control_model import HealthState, ObsState
from tango import DevState
import json
from ska_tmc_centralnode_mid.const import ModesAvailability

class Component:
    """
    A component manager for Central Node

    It supports:

    * Maintaining a connection to its component

    * Monitoring its component
    """

    def __init__(self, _faulty=False):
        self._faulty = _faulty
        self._devices = []
        self._telescope_state = DevState.UNKNOWN
        self._tmc_op_state = DevState.UNKNOWN
        self._telescope_health_state = HealthState.UNKNOWN
        self._health_state = HealthState.OK
        self._vlbi = ModesAvailability.not_available
        self._imaging = ModesAvailability.not_available
        self._pss = ModesAvailability.not_available
        self._pst = ModesAvailability.not_available

    def update_faulty(self, faulty):
        """
        Set component faulty

        :param faulty: boolean
        """
        self._faulty = faulty

    @property
    def faulty(self):
        """
        Return whether this component is currently experiencing a fault.

        :return: whether this component is faulting
        :rtype: bool
        """
        return self._faulty

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

    def update_device(self, devInfo):
        """
        Update (or add if missing) Device Information into the list of the component.

        :param devInfo: a DeviceInfo object
        """
        if devInfo not in self._devices:
            self._devices.append(devInfo)
        else:
            index = self._devices.index(devInfo)
            self._devices[index] = devInfo

    def update_device_exception(self, devInfo, exception):
        """
        Update (or add if missing) Device Information into the list of the component.

        :param devInfo: a DeviceInfo object
        """
        if devInfo not in self._devices:
            self._devices.append(devInfo)
        else:
            index = self._devices.index(devInfo)
            self._devices[index].exception = exception

    @property
    def telescope_state(self):
        """
        Return the telescope state

        :return: the telescope state
        :rtype: DevState
        """
        return self._telescope_state

    def set_telescope_state(self, value):
        """
        Set telescope state

        :param value: the new telescope state
        :type value: DevState
        """
        if isinstance(value, DevState):
            self._telescope_state = value

    @property
    def telescope_health_state(self):
        """
        Return the telescope health state

        :return: the telescope health state
        :rtype: HealthState
        """
        return self._telescope_health_state

    def set_telescope_health_state(self, value):
        """
        Set telescope health state

        :param value: the new telescope health state
        :type value: HealthState
        """
        if isinstance(value, HealthState):
            self._telescope_health_state = value

    @property
    def cn_health_state(self):
        """
        Return the telescope health state

        :return: the telescope health state
        :rtype: HealthState
        """
        return self._health_state

    def set_cn_health_state(self, value):
        """
        Set telescope health state

        :param value: the new telescope health state
        :type value: HealthState
        """
        if isinstance(value, HealthState):
            self._health_state = value

    @property
    def tmc_op_state(self):
        """
        Return the TMC operational State

        :return: the TMC operational State
        :rtype: DevState
        """
        return self._tmc_op_state

    def set_tmc_op_state(self, value):
        """
        Set the TMC operational State

        :param value: the TMC operational State
        :type value: DevState
        """
        if isinstance(value, DevState):
            self._tmc_op_state = value

    @property
    def vlbi(self):
        """
        Return vlbi ModesAvailability

        :return: vlbi ModesAvailability
        :rtype: ModesAvailability
        """
        return self._vlbi

    def set_vlbi(self, value):
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

    def set_imaging(self, value):
        """
        Set vlbi ModesAvailability

        :param value: vlbi ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            self._imaging = value

    @property
    def pss(self):
        """
        Return pss ModesAvailability

        :return: pss ModesAvailability
        :rtype: ModesAvailability
        """
        return self._pss

    def set_pss(self, value):
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

    def set_pst(self, value):
        """
        Set pss ModesAvailability

        :param value: pss ModesAvailability
        :type value: ModesAvailability
        """
        if isinstance(value, ModesAvailability):
            self._pst = value

    @property
    def sub_array_obs_state(self, id):

        """
        Return the subarray obsState

        :param id: id of the subarray
        :return: the subarray obsState
        :rtype: ObsState
        """
        for devInfo in self._devices:
            if isinstance(devInfo, SubArrayDeviceInfo):
                if devInfo.id == id:
                    return devInfo.obsState
        return None

    def default(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        devices = []
        for dev in self.devices:
            devices.append(dev.to_dict())
        result = {
            "telescope_state": self._telescope_state,
            "tmc_op_state": self._tmc_op_state,
            "telescope_health_state": self._telescope_health_state,
            "devices": devices
        }

        return result

class DeviceInfo:
    def __init__(self):
        self.dev_name = ""
        self.state = DevState.UNKNOWN
        self.obsState = ObsState.EMPTY
        self.healthState = HealthState.UNKNOWN
        self.ping = -1
        self.last_event_arrived = None
        self.exception = None

    def __eq__(self, other):
        if (isinstance(other, DeviceInfo)):
            return self.dev_name == other.dev_name

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        result = {
            "dev_name": self.dev_name,
            "state": self.state,
            "obsState": self.obsState,
            "healthState": self.healthState,
            "ping": str(self.ping),
            "last_event_arrived": str(self.last_event_arrived),
            "exception_occurred": str(self.exception)
        }
        return result

class SubArrayDeviceInfo(DeviceInfo):
    def __init__(self):
        self.id = -1
        self.resources = []

    def __eq__(self, other):
        if (isinstance(other, SubArrayDeviceInfo)):
            return self.dev_name == other.dev_name

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        super_dict = super().to_dict()
        result = []
        for res in self.resources:
            result.append(res)
        super_dict['resources'] = result
        return super_dict


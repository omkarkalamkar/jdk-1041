import threading
from ska_tango_base.control_model import HealthState, ObsState
from tango import DevState
import json
from ska_tmc_centralnode_mid.const import ModesAvailability

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

    def set_op_callbacks(self, 
        _update_device_callback = None,
        _update_telescope_state_callback = None,
        _update_telescope_health_state_callback = None,
        _update_tmc_op_state_callback = None,
        _update_subarray_health_state_callback = None,):
        self._update_device_callback = _update_device_callback
        self._update_telescope_state_callback = _update_telescope_state_callback
        self._update_telescope_health_state_callback = _update_telescope_health_state_callback
        self._update_tmc_op_state_callback = _update_tmc_op_state_callback
        self._update_subarray_health_state_callback = _update_subarray_health_state_callback

    def _invoke_device_callback(self, devInfo):
        if self._update_device_callback is not None:
            self._update_device_callback(devInfo)

    def _invoke_telescope_state_callback(self):
        if self._update_telescope_state_callback is not None:
            self._update_telescope_state_callback(self.telescope_state)

    def _invoke_telescope_health_state_callback(self):
        if self._update_telescope_health_state_callback is not None:
            self._update_telescope_health_state_callback(self.telescope_health_state)
    
    def _invoke_tmc_op_state_callback(self):
        if self._update_tmc_op_state_callback is not None:
            self._update_tmc_op_state_callback(self.tmc_op_state)

    def _invoke_subarray_health_state_callback(self, devInfo):
        if self._update_subarray_health_state_callback is not None:
            self._update_subarray_health_state_callback(devInfo)
    
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

        self._invoke_device_callback(devInfo)

    def update_device_exception(self, devInfo, exception):
        """
        Update (or add if missing) Device Information into the list of the component.

        :param devInfo: a DeviceInfo object
        """
        if devInfo not in self._devices:
            self._devices.append(devInfo)
            self._invoke_device_callback(devInfo)
        else:
            index = self._devices.index(devInfo)
            intDevInfo = self._devices[index]
            intDevInfo.state = DevState.UNKNOWN
            intDevInfo.update_faulty(True, exception)
            self._invoke_device_callback(intDevInfo)

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

    def set_telescope_health_state(self, value):
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
    def cn_health_state(self):
        """
        Return the central node health state

        :return: the central node health state
        :rtype: HealthState
        """
        return self._health_state

    # def set_cn_health_state(self, value):
    #     """
    #     Set central node health state

    #     :param value: the new central node health state
    #     :type value: HealthState
    #     """
    #     if isinstance(value, HealthState):
    #         self._health_state = value

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
    def __init__(self, dev_name: str, _faulty=False):
        self.dev_name = dev_name
        self.state = DevState.UNKNOWN
        self.obsState = ObsState.EMPTY
        self.healthState = HealthState.UNKNOWN
        self.ping = -1
        self.last_event_arrived = None
        self.exception = None
        self._faulty = _faulty
        self.lock = threading.Lock()

    def from_dev_info(self, devInfo):
        self.dev_name = devInfo.dev_name
        self.state = devInfo.state
        self.obsState = devInfo.obsState
        self.healthState = devInfo.healthState
        self.ping = devInfo.ping
        self.last_event_arrived = devInfo.last_event_arrived
        self.exception = devInfo.exception
        self._faulty = devInfo.faulty
        self.lock = devInfo.lock

    def update_faulty(self, faulty, exception):
        """
        Set device faulty

        :param faulty: boolean
        """
        self._faulty = faulty
        self.exception = exception
        if self._faulty:
            self.state = DevState.UNKNOWN
            self.obsState = ObsState.EMPTY
            self.healthState = HealthState.UNKNOWN
            self.ping = -1

    @property
    def faulty(self):
        """
        Return whether this device is currently experiencing a fault.

        :return: whether this device is faulting
        :rtype: bool
        """
        return self._faulty

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
    def __init__(self, dev_name, _faulty=False):
        super(SubArrayDeviceInfo, self).__init__(dev_name, _faulty)
        self.id = -1
        self.resources = []

    def from_dev_info(self, subarrayDevInfo):
        super().from_dev_info(subarrayDevInfo)
        if (isinstance(subarrayDevInfo, SubArrayDeviceInfo)):
            self.id = subarrayDevInfo.id
            self.resources = subarrayDevInfo.resources

    def __eq__(self, other):
        if (isinstance(other, SubArrayDeviceInfo) or isinstance(other, DeviceInfo)):
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


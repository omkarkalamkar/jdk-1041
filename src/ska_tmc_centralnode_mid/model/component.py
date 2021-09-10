from ska_tango_base.control_model import HealthState, ObsState
from tango import DevState

class Component:
    """
    A component manager for Central Node

    It supports:

    * Maintaining a connection to its component

    * Monitoring its component
    """

    def __init__(self, _faulty=False):
        self._faulty = _faulty
        self._update_model_callback = None
        self._fault_callback = None
        self._devices = []
        self._telescope_state = DevState.UNKNOWN
        self._tmc_op_state = DevState.UNKNOWN
        self._telescope_health_state = HealthState.UNKNOWN


    def set_op_callbacks(self, update_model_callback, fault_callback):
        """
        Set callbacks for the underlying component.

        :param update_model_callback: a callback to call when the
            model of the component changes
        :param fault_callback: a callback to call when the component
            experiences a fault
        """
        self._update_model_callback = update_model_callback
        self._fault_callback = fault_callback

    def add_device(self, devInfo):
        """
        Add Device Information into the list of the component.

        :param devInfo: a DeviceInfo object
        """
        if devInfo not in self._devices:
            self._devices.append(devInfo)
        else:
            index = self._devices.index(devInfo)
            self._devices[index] = devInfo

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

    @property
    def sub_array_obs_state(self, id):

        """
        Return the subarray obsState

        :param id: id of the subarray
        :return: the subarray obsState
        :rtype: ObsState
        """
        for devInfo in self._devices:
            if isinstance(devInfo, DeviceInfoRes):
                if devInfo.id == id:
                    return devInfo.obsState
        return None


class DeviceInfo:
    def __init__(self):
        self.dev_name = ""
        self.state = DevState.UNKNOWN
        self.obsState = ObsState.EMPTY
        self.healthState = HealthState.UNKNOWN
        self.ping = -1
        self.last_event_arrived = None

    def __eq__(self, other):
        if (isinstance(other, DeviceInfo)):
            return self.dev_name == other.dev_name

class DeviceInfoRes(DeviceInfo):
    def __init__(self):
        self.id = -1
        self.resources = []

    def __eq__(self, other):
        if (isinstance(other, DeviceInfoRes)):
            return self.dev_name == other.dev_name

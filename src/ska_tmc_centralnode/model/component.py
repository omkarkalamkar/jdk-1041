import json
import threading

from ska_control_model import HealthState
from ska_tmc_common.device_info import DeviceInfo
from ska_tmc_common.tmc_component_manager import TmcComponent
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

    def _invoke_device_callback(self, dev_info):
        if self._update_device_callback is not None:
            self._update_device_callback(dev_info)

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

    def _invoke_imaging_callback(self):
        if self._update_imaging_callback is not None:
            self._update_imaging_callback(self.imaging)

    def _invoke_telescope_availability_callback(self):
        if self._telescope_availability_callback is not None:
            self._telescope_availability_callback(self.telescope_availability)

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
        for dev_info in self.devices:
            if dev_info.dev_name == dev_name:
                return dev_info
        return None

    def remove_device(self, dev_name):
        """
        Remove a device from the list

        :param dev_name: name of the device
        """
        for dev_info in self.devices:
            if dev_info.dev_name == dev_name:
                self.devices.remove(dev_info)

    def update_device(self, dev_info):
        """
        Update (or add if missing) Device Information into the list of the component.

        :param dev_info: a DeviceInfo object
        """
        if dev_info not in self._devices:
            self._devices.append(dev_info)
        else:
            index = self._devices.index(dev_info)
            self._devices[index] = dev_info
        self.logger.info("Devices added are: %s", self.devices)
        self._invoke_device_callback(dev_info)

    def update_device_exception(self, dev_info, exception):
        """
        Update (or add if missing) Device Information into the list of the component.

        :param dev_info: a DeviceInfo object
        """
        if dev_info not in self._devices:
            dev_info.update_unresponsive(True, exception)
            self._devices.append(dev_info)
            self._invoke_device_callback(dev_info)
        else:
            index = self._devices.index(dev_info)
            intdev_info = self._devices[index]
            intdev_info.state = DevState.UNKNOWN
            intdev_info.update_unresponsive(True, exception)
            self._invoke_device_callback(intdev_info)

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
    def telescope_availability(self):
        """
        Returns the telescope availability

        :return: the telescope availability
        :rtype: DevVarStringArray
        """
        return self._telescope_availability

    @telescope_availability.setter
    def telescope_availability(self, value):
        """
        Set telescope availability

        :param value: the new telescope availability
        :type value: DevState
        """
        if self._telescope_availability != value:
            self._telescope_availability = value
            self._invoke_telescope_availability_callback()

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


class MCCSDeviceInfo(DeviceInfo):
    def __init__(self, dev_name, _unresponsive=False):
        super(MCCSDeviceInfo, self).__init__(dev_name, _unresponsive)
        self.resources = {}

    def from_dev_info(self, mccsdev_info):
        super().from_dev_info(mccsdev_info)
        if isinstance(mccsdev_info, MCCSDeviceInfo):
            self.resources = mccsdev_info.resources

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

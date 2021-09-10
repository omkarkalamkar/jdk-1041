"""
This module provided a reference implementation of a BaseComponentManager.

It is provided for explanatory purposes, and to support testing of this
package.
"""
import threading
from ska_tango_base.base import BaseComponentManager

from ska_tmc_centralnode_mid.model.component import Component

class CNComponentManager(BaseComponentManager):
    """
    A component manager for The Central Node component.

    It supports:

    * Maintaining a connection to its component

    * Controlling its component via commands like Off(), Standby(),
      On(), etc.

    * Monitoring its component, e.g. detect that it has been turned off
      or on

    The current implementation is intended to

    * illustrate the model

    * enable testing of these base classes

    It should not generally be used in concrete devices; instead, write
    a component manager specific to the component managed by the device.
    """

    def __init__(self, 
        op_state_model, 
        logger=None, 
        _component=None,
        _update_device_callback = None,
        _update_telescope_state_callback = None,
        _update_telescope_health_state_callback = None,
        _update_tmc_health_state_callback = None,
        _update_subarray_health_state_callback = None,
        *args, **kwargs):
        """
        Initialise a new ComponentManager instance.

        :param op_state_model: the op state model used by this component
            manager
        :param logger: a logger for this component manager
        :param _component: allows setting of the component to be
            managed; for testing purposes only
        """
        self.logger = logger

        self._component = _component or Component()

        self._lock = threading.Lock()

        self._update_device_callback = _update_device_callback
        self._update_telescope_state_callback = _update_telescope_state_callback
        self._update_telescope_health_state_callback = _update_telescope_health_state_callback
        self._update_tmc_health_state_callback = _update_tmc_health_state_callback
        self._update_subarray_health_state_callback = _update_subarray_health_state_callback

        super().__init__(op_state_model, *args, **kwargs)

    @property
    def faulty(self):
        """
        Whether the component is currently faulting.

        :return: whether the component is faulting
        """
        return self._component.faulty

    @property
    def devices(self):
        """
        Return the list of the monitored devices 

        :return: list of the monitored devices
        """
        return self._component.devices


    def component_fault(self):
        """
        Handle notification that the component has faulted.

        This is a callback hook.
        """
        self.op_state_model.perform_action("component_fault")

    def device_failed(self, device_info, exception):
        with self._lock:
            self._component.update_device_exception(device_info, exception)

        self._update_device_callback()

    def update_device_info(self, device_info):
        with self._lock:
            self._component.update_device(device_info)
            self._update_device_callback()

    def update_device_health_state(self, dev_name, health_state):
        devInfo = self._component.get_device(dev_name)
        with self._lock:
            devInfo.healthState = health_state
            self._aggregate_health_state()
            self._update_device_callback()
            self._update_telescope_health_state_callback()

    def update_device_state(self, dev_name, state):
        devInfo = self._component.get_device(dev_name)
        with self._lock:
            devInfo.state = state
            self._aggregate_state()
            self._update_device_callback()
            self._update_telescope_state_callback()

    def update_device_obs_state(self, dev_name, obs_state):
        devInfo = self._component.get_device(dev_name)
        with self._lock:
            devInfo.obsState = obs_state
            self._update_device_callback()
        
        self._update_resources(dev_name)

    def _aggregate_health_state(self):
        pass

    def _aggregate_state(self):
        pass

    def _update_resources(self, subarray_dev_name):
        pass


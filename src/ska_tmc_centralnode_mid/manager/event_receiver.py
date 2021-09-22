import threading
from time import sleep
from ska_tmc_centralnode_mid import dev_factory
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from ska_tmc_centralnode_mid.model.component import DeviceInfo, SubArrayDeviceInfo
from concurrent import futures
import tango

class EventReceiver:
    """
    The EventReceiver class has the responsibility to receive events
    from the sub devices managed by the central node.

    The ComponentManager uses the handle events methods
    for the attribute of interest. 
    For each of them a callback is defined. 

    TBD: what about scalability? what if we have 1000 devices? 

    """

    def __init__(self, component_manager, logger=None, max_workers = 1, proxy_timeout=500, sleep_timeout=1):
        self._thread = threading.Thread(target=self.run)
        self._stop = False
        self._logger = logger
        self._thread.setDaemon(True)
        self._component_manager = component_manager
        self._proxy_timeout = proxy_timeout
        self._sleep_timeout = sleep_timeout
        self._max_workers = max_workers
        self._dev_factory = DevFactory()

    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        self._stop = True
        self._thread.join()

    def run(self):
        while not self._stop:
            with futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                for devInfo in self._component_manager.devices:
                    if devInfo.last_event_arrived is None:
                        executor.submit(self.subscribe_events, devInfo)
            sleep(self._sleep_timeout)

    def subscribe_events(self, devInfo):
        try:
            proxy = self._dev_factory.get_device(devInfo.dev_name)
            proxy.subscribe_event("healthState",tango.EventType.CHANGE_EVENT,self.handle_health_state_event,stateless=True)
            proxy.subscribe_event("State",tango.EventType.CHANGE_EVENT,self.handle_state_event,stateless=True)
            proxy.subscribe_event("ObsState",tango.EventType.CHANGE_EVENT,self.handle_obs_state_event,stateless=True)
        except:
            self._logger.debug("event not working for device %s", proxy.dev_name)

    def handle_health_state_event(self, evt):
        # import debugpy; debugpy.debug_this_thread()
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            return

        new_value = evt.attr_value.value
        self._component_manager.update_device_health_state(evt.device.dev_name(), new_value)

    def handle_state_event(self, evt):
        # import debugpy; debugpy.debug_this_thread()
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            return

        new_value = evt.attr_value.value
        self._component_manager.update_device_state(evt.device.dev_name(), new_value)

    def handle_obs_state_event(self, evt):
        # import debugpy; debugpy.debug_this_thread()
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            return

        new_value = evt.attr_value.value
        self._component_manager.update_device_obs_state(evt.device.dev_name(), new_value)
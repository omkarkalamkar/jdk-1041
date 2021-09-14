import threading
from time import sleep
from ska_tmc_centralnode_mid import dev_factory
from ska_tmc_centralnode_mid.dev_factory import DevFactory
from ska_tmc_centralnode_mid.model.component import DeviceInfo, SubArrayDeviceInfo
from concurrent import futures
import tango

class MonitoringLoop:
    """
    The MonitoringLoop class has the responsibility to monitor
    the sub devices managed by the central node.

    The ComponentManager uses the handle events methods
    for the attribute of interest. 
    For each of them a callback is defined. 

    """

    def __init__(self, component_manager, logger=None, max_workers = 1, proxy_timeout=500, sleep_timeout=1):
        self._thread = threading.Thread(target=self.run)
        self._stop = False
        self._logger = logger
        self._thread.setDaemon(True)
        self._lock = threading.Lock
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
                    executor.submit(self.device_task, devInfo)
            sleep(self._sleep_timeout)

    def device_task(self, devInfo):
        with tango.EnsureOmniThread():
            try:
                # import debugpy; debugpy.debug_this_thread()
                self._logger.debug("Checking device %s", devInfo.dev_name)
                proxy = self._dev_factory.get_device(devInfo.dev_name)
                if devInfo.last_event_arrived is None:
                    proxy.subscribe_event("healthState",tango.EventType.CHANGE_EVENT,self.handle_health_state_event,stateless=True)
                    proxy.subscribe_event("State",tango.EventType.CHANGE_EVENT,self.handle_state_event,stateless=True)
                    proxy.subscribe_event("ObsState",tango.EventType.CHANGE_EVENT,self.handle_obs_state_event,stateless=True)
                proxy.set_timeout_millis(self._proxy_timeout)
                newDevInfo = None
                if "subarray" in devInfo.dev_name.lower():
                    newDevInfo = SubArrayDeviceInfo(devInfo.dev_name)
                else:
                    newDevInfo = DeviceInfo(devInfo.dev_name)
                newDevInfo.from_dev_info(devInfo)
                newDevInfo.ping = proxy.ping()
                newDevInfo.state = proxy.State()
                newDevInfo.obsState = proxy.obsState
                newDevInfo.healthState = proxy.healthState
                newDevInfo.dev_info = proxy.info()
                self._component_manager.update_device_info(newDevInfo)
            except Exception as e:
                self._logger.debug("device not working %s", devInfo.dev_name)
                self._component_manager.device_failed(devInfo, e)

    def handle_health_state_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            return

        new_value = evt.attr_value.value
        self._component_manager.update_device_health_state(evt.device.dev_name(), new_value)

    def handle_state_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            return

        new_value = evt.attr_value.value
        self._component_manager.update_device_state(evt.device.dev_name(), new_value)

    def handle_obs_state_event(self, evt):
        if evt.err:
            error = evt.errors[0]
            self._logger.error("%s %s", error.reason, error.desc)
            return

        new_value = evt.attr_value.value
        self._component_manager.update_device_obs_state(evt.device.dev_name(), new_value)
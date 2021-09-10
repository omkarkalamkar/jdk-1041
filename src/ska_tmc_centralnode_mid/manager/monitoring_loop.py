import threading
from time import sleep
from ska_tmc_centralnode_mid import dev_factory
from ska_tmc_centralnode_mid.dev_factory import dev_factory
from ska_tmc_centralnode_mid.model.component import DeviceInfo
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

    def __init__(self, component_manager, logger=None, max_workers = 5, proxy_timeout=500, sleep_timeout=1):
        self._thread = threading.Thread()
        self._stop = False
        self._logger = logger
        self._thread.setDaemon(True)
        self._lock = threading.Lock
        self._component_manager = component_manager
        self._proxy_timeout = proxy_timeout
        self._sleep_timeout = sleep_timeout
        self._max_workers = max_workers
        self._dev_factory = dev_factory()
        self._thread.start()

    def stop(self):
        self._stop = True
        self._thread.join()

    def run(self):
        with tango.EnsureOmniThread():
            while not self._stop:
                with futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                    for devInfo in self._component_manager.devices:
                        executor.submit(self.device_task, devInfo)
                sleep(self._sleep_timeout)

    def device_task(self, devInfo):
        with tango.EnsureOmniThread():
            try:
                proxy = self._dev_factory.get_device(devInfo.dev_name)
                proxy.set_timeout_millis(self._proxy_timeout)
                newDevInfo = DeviceInfo()
                newDevInfo.ping = proxy.ping()
                newDevInfo.state = proxy.State()
                newDevInfo.obsState = proxy.obsState
                newDevInfo.healthState = proxy.healthState
                newDevInfo.dev_info = proxy.info()
                self._component_manager.update_device(newDevInfo)
            except Exception as e:
                # device not working
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
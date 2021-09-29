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

    It is an infinite loop which ping, get the state, the obsState,
    the healthState and device information of the monitored SKA devices

    TBD: what about scalability? what if we have 1000 devices? 

    """

    def __init__(self, component_manager, logger=None, max_workers = 5, proxy_timeout=500, sleep_timeout=1):
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
                    executor.submit(self.device_task, devInfo)
            sleep(self._sleep_timeout)

    def device_task(self, devInfo):
        with tango.EnsureOmniThread():
            try:
                # import debugpy; debugpy.debug_this_thread()
                proxy = self._dev_factory.get_device(devInfo.dev_name)
                proxy.set_timeout_millis(self._proxy_timeout)
                newDevInfo = None
                if "subarray" in devInfo.dev_name.lower():
                    newDevInfo = SubArrayDeviceInfo(devInfo.dev_name)
                    newDevInfo.resources = proxy.assignedResources
                else:
                    newDevInfo = DeviceInfo(devInfo.dev_name)
                newDevInfo.from_dev_info(devInfo)
                newDevInfo.ping = proxy.ping()
                newDevInfo.state = proxy.State()
                newDevInfo.obsState = proxy.obsState
                newDevInfo.healthState = proxy.HealthState
                newDevInfo.dev_info = proxy.info()
                self._component_manager.update_device_info(newDevInfo)
            except Exception as e:
                self._logger.error("Device not working %s %s", devInfo.dev_name, e)
                self._component_manager.device_failed(devInfo, e)

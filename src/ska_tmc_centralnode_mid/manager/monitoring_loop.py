import threading
from concurrent import futures
from queue import Empty, Queue
from time import sleep

import numpy as np
import tango
from tango import AttrDataFormat

from ska_tmc_centralnode_mid.dev_factory import DevFactory
from ska_tmc_centralnode_mid.model.component import (
    DeviceInfo,
    MCCSDeviceInfo,
    SubArrayDeviceInfo,
)


class MonitoringLoop:
    """
    The MonitoringLoop class has the responsibility to monitor
    the sub devices managed by the central node.

    It is an infinite loop which ping, get the state, the obsState,
    the healthState and device information of the monitored SKA devices

    TBD: what about scalability? what if we have 1000 devices?

    """

    def __init__(
        self,
        component_manager,
        logger=None,
        max_workers=5,
        proxy_timeout=500,
        sleep_time=1,
    ):
        self._thread = threading.Thread(target=self.run)
        self._stop = False
        self._logger = logger
        self._thread.setDaemon(True)
        self._component_manager = component_manager
        self._proxy_timeout = proxy_timeout
        self._sleep_time = sleep_time
        self._max_workers = max_workers
        self._dev_factory = DevFactory()
        self._priority_devices = Queue(0)

    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        self._stop = True

    def add_priority_devices(self, dev_name):
        self._priority_devices.put(dev_name)

    def run(self):
        while not self._stop:
            with futures.ThreadPoolExecutor(
                max_workers=self._max_workers
            ) as executor:
                not_read_devices_twice = []
                try:
                    while not self._priority_devices.empty():
                        dev_name = self._priority_devices.get(block=False)
                        devInfo = self._component_manager.get_device(dev_name)
                        executor.submit(self.device_task, devInfo)
                        not_read_devices_twice.append(devInfo)
                except Empty:
                    pass

                for devInfo in self._component_manager.devices:
                    if devInfo not in not_read_devices_twice:
                        executor.submit(self.device_task, devInfo)

            sleep(self._sleep_time)

    def get_assignedResources_attributes(self, proxy):
        try:
            return proxy.attribute_query("assignedResources")
        except:
            return None

    def device_task(self, devInfo):
        with tango.EnsureOmniThread():
            try:
                # import debugpy; debugpy.debug_this_thread()
                proxy = self._dev_factory.get_device(devInfo.dev_name)
                proxy.set_timeout_millis(self._proxy_timeout)
                newDevInfo = None
                attrInfoEx = self.get_assignedResources_attributes(proxy)
                if attrInfoEx is None:
                    newDevInfo = DeviceInfo(devInfo.dev_name)
                    newDevInfo.from_dev_info(devInfo)
                else:
                    if attrInfoEx.data_format == AttrDataFormat.SCALAR:
                        newDevInfo = MCCSDeviceInfo(devInfo.dev_name)
                        newDevInfo.resources = proxy.assignedResources
                    else:
                        newDevInfo = SubArrayDeviceInfo(devInfo.dev_name)
                        newDevInfo.from_dev_info(devInfo)
                        assignedRes = proxy.assignedResources
                        if assignedRes is not None:
                            newDevInfo.resources = np.asarray(
                                proxy.assignedResources
                            )
                        else:
                            newDevInfo.resources = []
                        newDevInfo.obsState = proxy.obsState
                        for s in devInfo.dev_name:
                            if s.isdigit():
                                newDevInfo.id = int(s)

                newDevInfo.ping = proxy.ping()
                newDevInfo.state = proxy.State()
                newDevInfo.healthState = proxy.HealthState
                newDevInfo.dev_info = proxy.info()
                self._component_manager.update_device_info(newDevInfo)
            except Exception as e:
                self._logger.error(
                    "Device not working %s: %s", devInfo.dev_name, e
                )
                self._component_manager.device_failed(devInfo, e)

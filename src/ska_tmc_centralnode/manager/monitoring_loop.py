# TODO: Refactor/remove this class
# import json

# import numpy as np
# import tango
# from ska_tmc_common.device_info import DeviceInfo, SubArrayDeviceInfo
# from ska_tmc_common.monitoring_loop import MonitoringLoop
# from tango import AttrDataFormat

# from ska_tmc_centralnode.model.component import MCCSDeviceInfo


# class CentralNodeMonitoringLoop(MonitoringLoop):
#     """
#     The MonitoringLoop class has the responsibility to monitor
#     the sub devices managed by the central node.

#     It is an infinite loop which ping, get the state, the obsState,
#     the healthState and device information of the monitored SKA devices

#     TBD: what about scalability? what if we have 1000 devices?

#     """

#     def __init__(
#         self,
#         component_manager,
#         logger=None,
#         max_workers=5,
#         proxy_timeout=500,
#         sleep_time=1,
#     ):
#         super().__init__(
#             component_manager, logger, max_workers, proxy_timeout, sleep_time
#         )

#     def device_task(self, dev_info):
#         with tango.EnsureOmniThread():
#             try:
#                 # import debugpy; debugpy.debug_this_thread()
#                 proxy = self._dev_factory.get_device(dev_info.dev_name)
#                 new_dev_info = self.create_device_info(dev_info, proxy)
#                 proxy.set_timeout_millis(self._proxy_timeout)
#                 new_dev_info.ping = proxy.ping()
#                 new_dev_info.state = proxy.State()
#                 new_dev_info.health_state = proxy.HealthState
#                 new_dev_info.dev_info = proxy.info()
#                 self._component_manager.update_device_info(new_dev_info)
#             except Exception as e:
#                 self._logger.error(
#                     "Device %s not working. Check internalModel attribute.",
#                     dev_info.dev_name,
#                 )
#                 self._component_manager.device_failed(dev_info, e)

#     def create_device_info(self, devInfo, proxy):
#         newDevInfo = None
#         attrInfoEx = self.get_assignedResources_attributes(proxy)
#         if attrInfoEx is None:
#             newDevInfo = DeviceInfo(devInfo.dev_name)
#             newDevInfo.from_dev_info(devInfo)
#         else:
#             attrInfoEx = proxy.attribute_query("assignedResources")
#             if attrInfoEx.data_format == AttrDataFormat.SCALAR:
#                 newDevInfo = MCCSDeviceInfo(devInfo.dev_name)
#                 newDevInfo.resources = json.loads(proxy.assignedResources)
#             else:
#                 newDevInfo = SubArrayDeviceInfo(devInfo.dev_name)
#                 newDevInfo.from_dev_info(devInfo)
#                 assignedRes = proxy.assignedResources
#                 if assignedRes is not None:
#                     newDevInfo.resources = np.asarray(proxy.assignedResources)
#                 else:
#                     newDevInfo.resources = []
#                 newDevInfo.obs_state = proxy.obsState
#                 for s in devInfo.dev_name:
#                     if s.isdigit():
#                         newDevInfo.id = int(s)
#         return newDevInfo

#     def get_assignedResources_attributes(self, proxy):
#         attr_list = proxy.attribute_list_query()
#         for attr in attr_list:
#             if attr.name == "assignedResources":
#                 return attr
#         return None

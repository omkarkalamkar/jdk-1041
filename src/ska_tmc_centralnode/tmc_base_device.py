from ska_tango_base import SKABaseDevice
from tango import AttrWriteType
from tango.server import attribute, device_property


class TMCBaseDevice(SKABaseDevice):
    """
    Class for common attributes.
    """

    commandInProgress = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="commandInProgress attribute of Subarray Node.",
    )

    commandExecuted = attribute(
        dtype=(("DevString",),),
        max_dim_x=4,
        max_dim_y=100,
    )

    lastDeviceInfoChanged = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Json String representing the last device changed in the internal model.",
    )

    # -----------------
    # Device Properties
    # -----------------

    MaxWorkerMonitoringLoop = device_property(
        dtype="DevUShort", default_value=5
    )

    ProxyTimeoutMonitoringLoop = device_property(
        dtype="DevUShort", default_value=500
    )

    SleepTime = device_property(dtype="DevFloat", default_value=1)

    def read_commandInProgress(self):
        # if not issubclass(TMCBaseDevice, self.__class__):
        #     return self.component_manager.command_executor.command_in_progress
        # else:
        #     pass
        return self.component_manager.command_executor.command_in_progress

    def read_commandExecuted(self):
        """Return the commandExecuted attribute."""
        # if not issubclass(Common, self.__class__):
        result = []
        i = 0
        for command_executed in reversed(
            self.component_manager.command_executor.command_executed
        ):
            if i == 100:
                break
            single_res = [
                str(command_executed["Id"]),
                str(command_executed["Command"]),
                str(command_executed["ResultCode"]),
                str(command_executed["Message"]),
            ]
            result.append(single_res)
            i += 1
        return result
        # else:
        #     pass

    def read_lastDeviceInfoChanged(self):
        return self._LastDeviceInfoChanged

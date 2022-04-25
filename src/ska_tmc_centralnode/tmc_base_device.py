import json

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
        max_dim_y=1000,
    )

    lastDeviceInfoChanged = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Json String representing the last device changed in the internal model.",
    )

    lastCommandExecuted = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Last command executed as string: uniqueid, command name, .result and message",
    )

    internalModel = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Json String representing the entire internal model.",
    )

    transformedInternalModel = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Json String representing the entire internal model transformed for better reading.",
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
        if not issubclass(TMCBaseDevice, self.__class__):
            return self.component_manager.command_executor.command_in_progress

    def read_commandExecuted(self):
        """Return the commandExecuted attribute."""
        if not issubclass(TMCBaseDevice, self.__class__):
            result = []
            for command_executed in reversed(
                self.component_manager.command_executor.command_executed
            ):
                single_res = [
                    str(command_executed["Id"]),
                    str(command_executed["Command"]),
                    str(command_executed["ResultCode"]),
                    str(command_executed["Message"]),
                ]
                result.append(single_res)
            return result

    def read_lastDeviceInfoChanged(self):
        return self._LastDeviceInfoChanged

    def read_lastCommandExecuted(self):
        """Return the lastCommandExecuted attribute as list of string."""
        if not issubclass(TMCBaseDevice, self.__class__):
            for command_executed in reversed(
                self.component_manager.command_executor.command_executed
            ):
                single_res = "{0} {1} {2} {3}".format(
                    str(command_executed["Id"]),
                    str(command_executed["Command"]),
                    str(command_executed["ResultCode"]),
                    str(command_executed["Message"]),
                )
                return single_res

    def read_transformedInternalModel(self):
        if not issubclass(TMCBaseDevice, self.__class__):
            json_model = json.loads(self.component_manager.component.to_json())
            result = {}
            for dev in json_model["devices"]:
                dev_name = dev["dev_name"]
                del dev["dev_name"]
                result[dev_name] = dev
            if "CentralNode" in str(self.__class__):
                """Executes CentralNode device's read method."""
                result = self.read_device_transformedInternalModel(
                    result, json_model
                )
                return json.dumps(result)
            elif "SubarrayNode" in str(self.__class__):
                """Executes SubarrayNode device's read method."""
                result = self.read_device_transformedInternalModel(
                    result, json_model
                )
                return json.dumps(result)

    def read_internalModel(self):
        if not issubclass(TMCBaseDevice, self.__class__):
            internal_model = self.component_manager.component.to_json()
            if "SubarrayNode" in str(self.__class__):
                print(internal_model)
                sn_internal_model = self.read_device_internalModel(
                    json.loads(internal_model)
                )
                return json.dumps(sn_internal_model)
            return internal_model

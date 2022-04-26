import json

from ska_tango_base import SKABaseDevice
from tango.server import attribute, device_property


class TMCBaseDevice(SKABaseDevice):
    """
    Class for common attributes.
    """

    # -----------------
    # Device Properties
    # -----------------
    SleepTime = device_property(dtype="DevFloat", default_value=1)

    # -----------------
    # Attributes
    # -----------------

    @attribute(
        dtype="DevString",
        doc="commandInProgress attribute of TMC Nodes .",
    )
    def commandInProgress(self):
        if not issubclass(TMCBaseDevice, self.__class__):
            return self.component_manager.command_executor.command_in_progress

    @attribute(
        dtype=(("DevString",),),
        max_dim_x=4,
        max_dim_y=1000,
    )
    def commandExecuted(self):
        """Return the commandExecuted attribute."""
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

    @attribute(
        dtype="DevString",
        doc="Json String representing the last device info changed in the internal model.",
    )
    def lastDeviceInfoChanged(self):
        return self.last_device_info_changed

    @attribute(
        dtype="DevString",
        doc="Last command executed as string: uniqueid, command name, .result and message",
    )
    def lastCommandExecuted(self):
        """Return the lastCommandExecuted attribute as list of string."""
        command_executed = (
            self.component_manager.command_executor.command_executed[-1]
        )
        single_res = "{0} {1} {2} {3}".format(
            str(command_executed["Id"]),
            str(command_executed["Command"]),
            str(command_executed["ResultCode"]),
            str(command_executed["Message"]),
        )
        return single_res

    @attribute(
        dtype="DevString",
        doc="Json String representing the entire internal model transformed for better reading.",
    )
    def transformedInternalModel(self):
        json_model = json.loads(self.component_manager.component.to_json())
        result = {}
        for dev in json_model["devices"]:
            dev_name = dev["dev_name"]
            del dev["dev_name"]
            result[dev_name] = dev
        if "CentralNode" in str(self.__class__):
            result = self.read_device_transformedInternalModel(
                result, json_model
            )
            return json.dumps(result)
        elif "SubarrayNode" in str(self.__class__):
            result = self.read_device_transformedInternalModel(
                result, json_model
            )
            return json.dumps(result)

    @attribute(
        dtype="DevString",
        doc="Json String representing the entire internal model.",
    )
    def internalModel(self):
        internal_model = self.component_manager.component.to_json()
        if "SubarrayNode" in str(self.__class__):
            sn_internal_model = self.read_device_internalModel(
                json.loads(internal_model)
            )
            return json.dumps(sn_internal_model)
        return internal_model

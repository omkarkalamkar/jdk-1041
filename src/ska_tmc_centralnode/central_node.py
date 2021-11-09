"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
import json

from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property

from ska_tmc_centralnode import release
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.model.input import InputParameterMid
from ska_tmc_centralnode.model.op_state_model import TMCOpStateModel


class AbstractCentralNode(SKABaseDevice):
    """
    Central Node is a coordinator of the complete Telescope system

    """

    # -----------------
    # Device Properties
    # -----------------
    CentralAlarmHandler = device_property(
        dtype="str",
        doc="Device name of CentralAlarmHandler ",
    )

    TMAlarmHandler = device_property(
        dtype="str",
        doc="Device name of TMAlarmHandler ",
    )

    TMSubarrayNodes = device_property(
        dtype=("str",),
        doc="List of TM Mid Subarray Node devices",
        default_value=tuple(),
    )

    SkuidServiceNamePort = device_property(
        dtype="DevString",
        default_value="ska-ser-skuid-test-svc.tmcmid.svc.cluster.local:9870",
    )

    MaxWorkerMonitoringLoop = device_property(
        dtype="DevUShort", default_value=5
    )

    ProxyTimeoutMonitoringLoop = device_property(
        dtype="DevUShort", default_value=500
    )

    SleepTime = device_property(dtype="DevFloat", default_value=1)

    # ----------
    # Attributes
    # ----------

    telescopehealthstate = attribute(
        dtype=HealthState,
        doc="Health state of Telescope",
    )

    telescopestate = attribute(
        dtype="DevState",
        access=AttrWriteType.READ,
        doc="DevState of telescope",
    )

    desiredtelescopestate = attribute(
        dtype="DevState",
        access=AttrWriteType.READ,
        doc="desiredtelescopestate attribute of Central Node.",
    )

    commandinprogress = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="commandinprogress attribute of Central Node.",
    )

    tmopstate = attribute(
        dtype="DevState",
    )

    subarraydevnames = attribute(
        dtype=("DevString",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=16,
    )

    commandexecuted = attribute(
        dtype=(("DevString",),),
        max_dim_x=4,
        max_dim_y=100,
    )

    lastcommandexecuted = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Last command executed as string: uniqueid, command name, .result and message",
    )

    internalmodel = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Json String representing the entire internal model.",
    )

    transformedinternalmodel = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Json String representing the entire internal model transformed for better reading.",
    )

    lastdeviceinfochanged = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="Json String representing the last device changed in the internal model.",
    )

    def update_device_callback(self, devInfo):
        self._LastDeviceInfoChanged = devInfo.to_json()
        self.push_change_event("lastdeviceinfochanged", devInfo.to_json())

    def update_telescope_state_callback(self, telescope_state):
        self.logger.info("telescopestate %s", telescope_state)
        self.push_change_event("telescopestate", telescope_state)

    def update_command_in_progress_callback(self, command_in_progress):
        self.push_change_event("commandinprogress", command_in_progress)

    def update_telescope_health_state_callback(self, telescope_health_state):
        self.push_change_event("telescopehealthstate", telescope_health_state)

    def update_tmc_op_state_callback(self, tmc_op_state):
        self.push_change_event("tmopstate", tmc_op_state)

    # ---------------
    # General methods
    # ---------------
    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TMC CentralNode's init_device() method.
        """

        def do(self):
            """
            Initializes the attributes and properties of the Central Node.

            :return: A tuple containing a return code and a string message indicating status.
             The message is for information purpose only.

            :rtype: (ReturnCode, str)
            """
            super().do()
            device = self.target

            device._build_state = "{},{},{}".format(
                release.name, release.version, release.description
            )
            device._version_id = release.version
            device._LastDeviceInfoChanged = ""
            device.set_change_event("telescopehealthstate", True, False)
            device.set_change_event("telescopestate", True, False)
            device.set_change_event("LastDeviceInfoChanged", True, False)
            device.set_change_event("tmopstate", True, False)
            device.set_change_event("commandinprogress", True, False)

            device.op_state_model.perform_action("component_on")
            device.component_manager.command_executor.add_command_execution(
                "0", "Init", ResultCode.OK, ""
            )
            return (ResultCode.OK, "")

    def always_executed_hook(self):
        pass

    def delete_device(self):
        # if the init is called more than once
        # I need to stop all threads
        if hasattr(self, "component_manager"):
            self.component_manager.stop()

    # ------------------
    # Attributes methods
    # ------------------

    def read_telescopehealthstate(self):
        return self.component_manager.component.telescope_health_state

    def read_telescopestate(self):
        return self.component_manager.component.telescope_state

    def read_desiredtelescopestate(self):
        return self.component_manager.component.desired_telescope_state

    def read_commandinprogress(self):
        return self.component_manager.command_executor.command_in_progress

    def read_internalmodel(self):
        return self.component_manager.component.to_json()

    def read_transformedinternalmodel(self):
        json_model = json.loads(self.component_manager.component.to_json())
        result = {
            "telescope_state": json_model["telescope_state"],
            "tmc_op_state": json_model["tmc_op_state"],
            "telescope_health_state": json_model["telescope_health_state"],
        }
        for dev in json_model["devices"]:
            dev_name = dev["dev_name"]
            del dev["dev_name"]
            result[dev_name] = dev
        return json.dumps(result)

    def read_lastdeviceinfochanged(self):
        return self._LastDeviceInfoChanged

    def read_commandexecuted(self):
        """Return the commandexecuted attribute."""
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

    def read_lastcommandexecuted(self):
        """Return the lastcommandexecuted attribute as list of string."""
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

    def read_tmopstate(self):
        """Return the tmopstate attribute."""
        return self.component_manager.component.tmc_op_state

    def read_subarraydevnames(self):
        """Return the subarraydevnames attribute."""
        return self.component_manager.input_parameter.tm_subarray_dev_names

    def write_subarraydevnames(self, value):
        """Set the subarraydevnames attribute."""
        self.component_manager.input_parameter.tm_subarray_dev_names = value
        self.component_manager.update_input_parameter()

    # --------
    # Commands
    # --------

    def is_StartUpTelescope_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("StartUpTelescope")
        return handler.check_allowed()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="[ResultCode, information-only string]",
    )
    @DebugIt()
    def StartUpTelescope(self):
        """
        This command invokes SetOperateMode() command on DishLeadNode,
        TelescopeOn() command on CspMasterLeafNode, SdpMasterLeafNode and SubarrayNode
        """
        handler = self.get_command_object("StartUpTelescope")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_StandByTelescope_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("StandByTelescope")
        return handler.check_allowed()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="[ResultCode, information-only string]",
    )
    def StandByTelescope(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, TelescopeStandBy() command
        on CspMasterLeafNode and SdpMasterLeafNode and TelescopeOff() command
        on SubarrayNode.
        """
        handler = self.get_command_object("StandByTelescope")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_TelescopeOff_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("TelescopeOff")
        return handler.check_allowed()

    @command(dtype_out="DevVarLongStringArray")
    def TelescopeOff(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, Off() command
        on CspMasterLeafNode and SdpMasterLeafNode.

        """
        handler = self.get_command_object("TelescopeOff")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_TelescopeOn_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("TelescopeOn")
        return handler.check_allowed()

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def TelescopeOn(self):
        """
        This command invokes TelescopeOn() command on DishLeadNode, CspMasterLeafNode,
        SdpMasterLeafNode.
        """
        handler = self.get_command_object("TelescopeOn")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_On_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        """
        handler = self.get_command_object("On")
        return handler.check_allowed()

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def On(self):
        """
        This command invokes On command on DishLeadNode, TelescopeOn() command on CspMasterLeafNode,
        SdpMasterLeafNode.
        """
        handler = self.get_command_object("On")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_AssignResources_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state

        :rtype: boolean
        """
        handler = self.get_command_object("AssignResources")
        return handler.check_allowed()

    @command(
        dtype_in="str",
        doc_in="The string in JSON format. The JSON contains following values:\nsubarrayID: "
        "DevShort\ndish: JSON object consisting\n- receptor_ids: DevVarStringArray. "
        "The individual string should contain dish numbers in string format with "
        "preceding zeroes upto 3 digits. E.g. 0001, 0002",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def AssignResources(self, argin):
        """
        AssignResources command invokes the AssignResources command on lower level devices.
        """
        handler = self.get_command_object("AssignResources")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_ReleaseResources_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("ReleaseResources")
        return handler.check_allowed()

    @command(
        dtype_in="str",
        doc_in="The string in JSON format. The JSON contains following values:\nsubarrayID: "
        "releaseALL boolean as true and receptor_ids.",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def ReleaseResources(self, argin):
        """
        Release all the resources assigned to the given Subarray.
        """
        handler = self.get_command_object("ReleaseResources")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Standby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("Standby")
        return handler.check_allowed()

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Standby(self):
        """
        This command invokes Standby() command on CspMasterLeafNode,
        SdpMasterLeafNode and DishLeafNode.

        """
        handler = self.get_command_object("Standby")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_TelescopeStandby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("TelescopeStandby")
        return handler.check_allowed()

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def TelescopeStandby(self):
        """
        This command invokes TelescopeStandby() command on CspMasterLeafNode,
        SdpMasterLeafNode and DishLeafNode.

        """
        handler = self.get_command_object("TelescopeStandby")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Off_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """

        handler = self.get_command_object("Off")
        return handler.check_allowed()

    @command(
        dtype_out="DevVarLongStringArray",
    )
    def Off(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode,
        TelescopeOff() command on CspMasterLeafNode and
        SdpMasterLeafNode.

        """
        handler = self.get_command_object("Off")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler
        )
        return [[ResultCode.QUEUED], [str(unique_id)]]

    # default ska mid
    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManager(
            self.op_state_model,
            logger=self.logger,
            _update_device_callback=self.update_device_callback,
            _update_telescope_state_callback=self.update_telescope_state_callback,
            _update_telescope_health_state_callback=self.update_telescope_health_state_callback,
            _update_tmc_op_state_callback=self.update_tmc_op_state_callback,
            _update_imaging_callback=self.update_imaging_callback,
            _update_command_in_progress_callback=self.update_command_in_progress_callback,
            max_workers=self.MaxWorkerMonitoringLoop,
            proxy_timeout=self.ProxyTimeoutMonitoringLoop,
            _input_parameter=InputParameterMid(None),
            sleep_time=self.SleepTime,
        )
        cm.input_parameter.tm_dish_dev_names = []
        for dish in range(1, (self.NumDishes + 1)):
            cm.input_parameter.tm_dish_dev_names.append(
                self.DishLeafNodePrefix + f"000{dish}"
            )
        cm.input_parameter.dish_dev_names = []
        for dish in range(1, (self.NumDishes + 1)):
            cm.input_parameter.dish_dev_names.append(
                f"{'mid_d'}000{dish}{'/elt/master'}"
            )
        cm.input_parameter.tm_subarray_dev_names = self.TMSubarrayNodes
        cm.input_parameter.csp_master_dev_name = self.CspMasterFQDN or ""
        cm.input_parameter.tm_leaf_csp_master_dev_name = (
            self.CspMasterLeafNodeFQDN or ""
        )
        cm.input_parameter.sdp_master_dev_name = self.SdpMasterFQDN or ""
        cm.input_parameter.tm_leaf_sdp_master_dev_name = (
            self.SdpMasterLeafNodeFQDN or ""
        )
        cm.input_parameter.csp_subarray_dev_names = (
            self.TMMidCspSubarrayLeafNodes
        )
        cm.input_parameter.sdp_subarray_dev_names = (
            self.TMMidSdpSubarrayLeafNodes
        )
        cm.update_input_parameter()
        return cm

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()

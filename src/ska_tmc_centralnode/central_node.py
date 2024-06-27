"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
# pylint:disable = attribute-defined-outside-init
import json

import tango
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from ska_tmc_common.tmc_base_device import TMCBaseDevice
from tango import ApiUtil, AttrWriteType, DebugIt
from tango.server import attribute, command, device_property

from ska_tmc_centralnode import release


class AbstractCentralNode(TMCBaseDevice):
    """
    Central Node is a coordinator of the complete Telescope system.
    Central Node is inherited from TMCBaseDevice class which is further
    inherited from SKABaseDevice class. TMCBaseDevice class contains
    attributes common to CentralNode and SubarrayNode.
    """

    # -----------------
    # Device Properties
    # -----------------
    CentralAlarmHandler = device_property(
        dtype="str",
        doc="Device name of CentralAlarmHandler ",
    )

    TMCAlarmHandler = device_property(
        dtype="str",
        doc="Device name of TMCAlarmHandler ",
    )

    TMCSubarrayNodes = device_property(
        dtype=("str",),
        doc="List of TM Mid Subarray Node devices",
        default_value=tuple(),
    )

    AssignResourcesInterface = device_property(
        dtype="str",
        doc="Interface value of Asignresources schema",
    )

    ReleaseResourcesInterface = device_property(
        dtype="str",
        doc="Interface value of Asignresources schema",
    )

    CspMasterLeafNodeFQDN = device_property(dtype="str")

    CspMasterFQDN = device_property(dtype="str")

    SdpMasterLeafNodeFQDN = device_property(dtype="str")

    SdpMasterFQDN = device_property(dtype="str")

    CspSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of Low CspSubarrayLeafNode devices",
        default_value=tuple(),
    )

    SdpSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of Low SdpSubarrayLeafNode devices",
        default_value=tuple(),
    )

    SkuidService = device_property(
        dtype="DevString",
        default_value="ska-ser-skuid-test-svc.ska-tmc-centralnode"
        + ".svc.techops.internal.skao.int:9870",
    )

    MaxWorker = device_property(dtype="DevUShort", default_value=1)

    ProxyTimeout = device_property(dtype="DevUShort", default_value=500)

    CommandTimeout = device_property(dtype="DevUShort", default_value=30)
    # ----------
    # Attributes
    # ----------

    cspMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    sdpMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    CspMasterLeafNodeDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    SdpMasterLeafNodeDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    telescopeHealthState = attribute(
        dtype=HealthState,
        doc="Health state of Telescope",
    )

    telescopeState = attribute(
        dtype="DevState",
        access=AttrWriteType.READ,
        doc="DevState of telescope",
    )

    desiredTelescopeState = attribute(
        dtype="DevState",
        access=AttrWriteType.READ,
        doc="desiredTelescopeState attribute of Central Node.",
    )

    tmOpState = attribute(
        dtype="DevState",
    )

    subarrayDevNames = attribute(
        dtype=("DevString",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=16,
    )

    telescopeAvailability = attribute(
        dtype="str",
        access=AttrWriteType.READ,
    )

    def update_device_callback(self, devInfo):
        """Update device callabacks"""
        self.last_device_info_changed = devInfo.to_json()
        self.push_change_event("lastDeviceInfoChanged", devInfo.to_json())

    def update_telescope_state_callback(self, telescope_state):
        """Update telescope state callback"""
        self.logger.info("telescopeState %s", telescope_state)
        self.push_change_event("telescopeState", telescope_state)

    def update_telescope_health_state_callback(self, telescope_health_state):
        """Update Telescope health state callabacks"""
        self.push_change_event("telescopeHealthState", telescope_health_state)

    def update_tmc_op_state_callback(self, tmc_op_state):
        """Update tmc operational state callabacks"""
        self.push_change_event("tmOpState", tmc_op_state)

    def update_telescope_availability_callback(self, telescope_availability):
        """Update device availabililty callabacks"""
        self.push_change_event(
            "telescopeAvailability", json.dumps(telescope_availability)
        )

    # ---------------
    # General methods
    # ---------------
    class InitCommand(TMCBaseDevice.InitCommand):
        """
        A class for the TMC CentralNode's init_device() method.
        """

        def do(self):
            """
            Initializes the attributes and properties of the Central Node.

            :return: A tuple containing a return code and a string message
                indicating status.The message is for information purpose only.

            :rtype: (ReturnCode, str)
            """
            super().do()

            self._device._build_state = (
                f"{release.name},{release.version},{release.description}"
            )

            self._device._version_id = release.version
            self._device.last_device_info_changed = ""
            self._device.set_change_event("telescopeHealthState", True, False)
            self._device.set_change_event("telescopeState", True, False)
            self._device.set_change_event("lastDeviceInfoChanged", True, False)
            self._device.set_change_event("tmOpState", True, False)
            self._device.set_change_event("telescopeAvailability", True, False)
            ApiUtil.instance().set_asynch_cb_sub_model(
                tango.cb_sub_model.PUSH_CALLBACK
            )
            self._device._health_state = HealthState.OK
            self._device.op_state_model.perform_action("component_on")
            return (ResultCode.OK, "")

    def always_executed_hook(self):
        """always executed hook method"""

    def delete_device(self):
        # if the init is called more than once
        # I need to stop all threads
        if hasattr(self, "component_manager"):
            self.component_manager.stop()

    # ------------------
    # Attributes methods
    # ------------------
    def read_cspMasterDevName(self):
        """Return the cspMasterDevName attribute."""
        return self.component_manager.input_parameter.csp_master_dev_name

    def write_cspMasterDevName(self, value):
        """Set the cspMasterDevName attribute."""
        self.component_manager.input_parameter.csp_master_dev_name = value
        self.component_manager.update_input_parameter()

    def read_sdpMasterDevName(self):
        """Return the sdpMasterDevName attribute."""
        return self.component_manager.input_parameter.sdp_master_dev_name

    def write_sdpMasterDevName(self, value):
        """Set the sdpMasterDevName attribute."""
        self.component_manager.input_parameter.sdp_master_dev_name = value
        self.component_manager.update_input_parameter()

    def read_CspMasterLeafNodeDevName(self):
        """Return the cspMasterLeafNodeDevName attribute."""
        return self.component_manager.input_parameter.csp_mln_dev_name

    def write_CspMasterLeafNodeDevName(self, value):
        """Set the cspMasterLeafNodeDevName attribute."""
        self.component_manager.input_parameter.csp_mln_dev_name = value
        self.component_manager.update_input_parameter()

    def read_SdpMasterLeafNodeDevName(self):
        """Return the sdpMasterLeafNodeDevName attribute."""
        return self.component_manager.input_parameter.sdp_mln_dev_name

    def write_SdpMasterLeafNodeDevName(self, value):
        """Set the sdpMasterLeafNodeDevName attribute."""
        self.component_manager.input_parameter.sdp_mln_dev_name = value
        self.component_manager.update_input_parameter()

    def read_telescopeHealthState(self):
        """Read value of telescopeHealthState"""
        return self.component_manager.component.telescope_health_state

    def read_telescopeState(self):
        """Reads telescopeState"""
        return self.component_manager.component.telescope_state

    def read_desiredTelescopeState(self):
        """Read Desired TelescopeState"""
        return self.component_manager.component.desired_telescope_state

    def transformedInternalModel_read(self):
        """Tranformed InternalModelRead"""
        result = json.loads(super().transformedInternalModel_read())
        result[
            "telescope_state"
        ] = self.component_manager.get_telescope_state()
        result["tmc_op_state"] = self.component_manager.get_tmc_op_state()
        result[
            "telescope_health_state"
        ] = self.component_manager.get_telescope_health_state()
        return json.dumps(result)

    def read_tmOpState(self):
        """Return the tmOpState attribute."""
        return self.component_manager.component.tmc_op_state

    def read_subarrayDevNames(self):
        """Return the subarrayDevNames attribute."""
        return self.component_manager.input_parameter.subarray_dev_names

    def write_subarrayDevNames(self, value):
        """Set the subarrayDevNames attribute."""
        self.component_manager.input_parameter.subarray_dev_names = value
        self.component_manager.update_input_parameter()

    def read_telescopeAvailability(self):
        "Returns telescope availability"
        return json.dumps(
            self.component_manager.component.telescope_availability
        )

    # --------
    # Commands
    # --------

    def is_TelescopeOn_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
            state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("TelescopeOn")

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def TelescopeOn(self):
        """
        This command invokes TelescopeOn() command on DishLeadNode,
        CspMasterLeafNode,SdpMasterLeafNode.
        """
        handler = self.get_command_object("TelescopeOn")
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_TelescopeStandby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("TelescopeStandby")

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
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_TelescopeOff_allowed(self):
        """
        Checks whether this command is allowed to be run in current
        device state.

        :return: True if this command is allowed to be run in current
            device state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("TelescopeOff")

    @command(dtype_out="DevVarLongStringArray")
    def TelescopeOff(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, Off()
        command on CspMasterLeafNode and SdpMasterLeafNode.

        """
        handler = self.get_command_object("TelescopeOff")
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_On_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean

        """
        return self.component_manager.is_command_allowed("On")

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def On(self):
        """
        This command invokes On command on DishLeadNode, TelescopeOn()
            command on CspMasterLeafNode,SdpMasterLeafNode.
        """
        handler = self.get_command_object("On")
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_Off_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("Off")

    @command(
        dtype_out="DevVarLongStringArray",
    )
    def Off(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode,
        TelescopeOff() command on CspMasterLeafNode and SdpMasterLeafNode.
        """
        handler = self.get_command_object("Off")
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_Standby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("Standby")

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
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_AssignResources_allowed(self):
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("AssignResources")

    @command(
        dtype_in="str",
        doc_in="The string in JSON format. The JSON contains following values:"
        "nsubarrayID: "
        "DevShort\ndish: JSON object consisting\n- receptor_ids:"
        " DevVarStringArray. "
        "The individual string should contain dish numbers in string"
        " format with "
        "preceding zeroes upto 3 digits. E.g. SKA001, SKA002",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def AssignResources(self, argin):
        """
        AssignResources command invokes the AssignResources command on
            lower level devices.
        """
        handler = self.get_command_object("AssignResources")
        result_code, unique_id = handler(argin)
        return [[result_code], [str(unique_id)]]

    def is_ReleaseResources_allowed(self):
        """
        Checks whether ReleaseResources command is allowed to be run in
            current device state.

        :return: True if ReleaseResources command is allowed to be
            run in current device state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("ReleaseResources")

    @command(
        dtype_in="str",
        doc_in="The string in JSON format. The JSON contains following values:"
        "\nsubarrayID: "
        "releaseALL boolean as true and receptor_ids.",
        dtype_out="DevVarLongStringArray",
        doc_out="information-only string",
    )
    @DebugIt()
    def ReleaseResources(self, argin):
        """
        Releases all the resources assigned to the given Subarray.
        """
        handler = self.get_command_object("ReleaseResources")
        result_code, unique_id = handler(argin)
        return [[result_code], [str(unique_id)]]

    def create_component_manager(self):
        """Create component manager object for command invocation."""

    # TODO: Check with OET if these commands are required, else can be removed
    # def is_StartUpTelescope_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current
    #     device state.

    #     :return: True if this command is allowed to be run in
    #       current device state.

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("StartUpTelescope")
    #     return handler.check_allowed()

    # @command(
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="[ResultCode, information-only string]",
    # )
    # @DebugIt()
    # def StartUpTelescope(self):
    #     """
    #     This command invokes SetOperateMode() command on DishLeadNode,
    #     TelescopeOn() command on CspMasterLeafNode, SdpMasterLeafNode
    #      and SubarrayNode
    #     """
    #     self.log_state(
    #         "Device states before executing Telescope StartUp command"
    #     )
    #     handler = self.get_command_object("StartUpTelescope")
    #     if self.component_manager.command_executor.queue_full:
    #         return [[ResultCode.FAILED], ["Queue is full!"]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     self.log_state(
    #         "Device states after executing Telescope StartUp command"
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_StandByTelescope_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current
    #     device state.

    #     :return: True if this command is allowed to be run in current
    #     device state.

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("StandByTelescope")
    #     return handler.check_allowed()

    # @command(
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="[ResultCode, information-only string]",
    # )
    # def StandByTelescope(self):
    #     """
    #     This command invokes SetStandbyLPMode() command on DishLeafNode,
    #      TelescopeStandBy() command
    #     on CspMasterLeafNode and SdpMasterLeafNode and TelescopeOff command
    #     on SubarrayNode.
    #     """
    #     self.log_state(
    #         "Device states before executing Telescope StandBy command"
    #     )
    #     handler = self.get_command_object("StandByTelescope")
    #     if self.component_manager.command_executor.queue_full:
    #         return [[ResultCode.FAILED], ["Queue is full!"]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     self.log_state(
    #         "Device states after executing Telescope StandBy command"
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        for command_name, method_name in [
            ("TelescopeOn", "telescope_on"),
            ("TelescopeStandby", "telescope_standby"),
            ("TelescopeOff", "telescope_off"),
            ("AssignResources", "assign_resources"),
            ("ReleaseResources", "release_resources"),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name,
                    self._command_tracker,
                    self.component_manager,
                    method_name,
                    logger=None,
                ),
            )

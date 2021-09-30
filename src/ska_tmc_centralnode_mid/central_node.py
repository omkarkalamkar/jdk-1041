"""
Central Node is a coordinator of the complete M&C system. 
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Tango imports
import json
from tango import DebugIt, AttrWriteType, DevState, DevString
from tango.server import run, attribute, command, device_property

from ska_tmc_centralnode_mid.manager.component_manager import CNComponentManager
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateModel

# Additional import
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from ska_tmc_centralnode_mid.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode_mid.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode_mid.commands.telescope_standby_command import TelescopeStandby
from ska_tmc_centralnode_mid.commands.assign_resources_command import AssignResources
from ska_tmc_centralnode_mid.commands.release_resources_command import ReleaseResources
from ska_tmc_centralnode_mid.commands.stow_antennas_command import StowAntennas
from ska_tmc_centralnode_mid.const import ModesAvailability


# PROTECTED REGION END #    //  CentralNode.additional_import

__all__ = [
    "CentralNode",
    "main"
]

class CentralNode(SKABaseDevice):
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

    TMMidSubarrayNodes = device_property(
        dtype=("str",),
        doc="List of TM Mid Subarray Node devices",
        default_value=tuple(),
    )

    NumDishes = device_property(
        dtype="uint",
        default_value=0,
        doc="Number of Dishes",
    )

    DishLeafNodePrefix = device_property(
        dtype="str", default_value="", doc="Device name prefix for Dish Leaf Node"
    )

    TMMidCspSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of TM Mid CspSubarrayLeafNode devices",
        default_value=tuple(),
    )

    TMMidSdpSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of TM Mid SdpSubarrayLeafNode devices",
        default_value=tuple(),
    )

    CspMasterLeafNodeFQDN = device_property(dtype="str")

    CspMasterFQDN = device_property(dtype="str")    

    SdpMasterLeafNodeFQDN = device_property(dtype="str")

    SdpMasterFQDN = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    telescopeHealthState = attribute(
        dtype=HealthState,
        doc="Health state of Telescope",
    )

    subarray1HealthState = attribute(
        dtype=HealthState,
        doc="Health state of Subarray1",
    )

    subarray2HealthState = attribute(
        dtype=HealthState,
        doc="Health state of Subarray2",
    )
    subarray3HealthState = attribute(
        dtype=HealthState,
    )

    telescopeState = attribute(
        dtype="DevState",
        access=AttrWriteType.READ,
        doc="DevState of telescope"
    )

    imaging = attribute(
        dtype=ModesAvailability,
        access=AttrWriteType.READ,
        doc="Imaging Attribute"
    )

    pss = attribute(
        dtype=ModesAvailability,
        access=AttrWriteType.READ,
        doc="PSS Attribute"
    )

    pst = attribute(
        dtype=ModesAvailability,
        access=AttrWriteType.READ,
        doc="PST Attribute"
    )

    vlbi = attribute(
        dtype=ModesAvailability,
        access=AttrWriteType.READ,
        doc="VLBI Attribute"
    )

    desiredTelescopeState = attribute(
        dtype="DevState",
        access=AttrWriteType.READ,
        doc="desiredTelescopeState attribute of Central Node.",
    )

    commandInProgress = attribute(
        dtype="DevString",
        access=AttrWriteType.READ,
        doc="commandInProgress attribute of Central Node.",
    )

    CspMasterDevName = attribute(
        dtype='DevString',
        access=AttrWriteType.READ_WRITE,
    )

    SdpMasterDevName = attribute(
        dtype='DevString',
        access=AttrWriteType.READ_WRITE,
    )

    LeafCspMasterDevName = attribute(
        dtype='DevString',
        access=AttrWriteType.READ_WRITE,
    )

    LeafSdpMasterDevName = attribute(
        dtype='DevString',
        access=AttrWriteType.READ_WRITE,
    )

    TMOpState = attribute(
        dtype='DevState',
    )

    SubarrayDevNames = attribute(
        dtype=('DevString',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=16,
    )

    CspSubarrayDevNames = attribute(
        dtype=('DevString',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=16,
    )

    SdpSubarrayDevNames = attribute(
        dtype=('DevString',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=16,
    )

    DishDevNames = attribute(
        dtype=('DevString',),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=100,
    )

    CommandExecuted = attribute(
        dtype=(('DevString',),),
        max_dim_x=4, max_dim_y=100,
    )
    
    InternalModel = attribute(
        dtype='DevString',
        access=AttrWriteType.READ,
        doc="Json String representing the entire internal model.",
    )

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger,
            callback=super()._update_state)
        cm =  CNComponentManager(
            self.op_state_model, 
            logger=self.logger,
            _update_device_callback = self.update_device_callback,
            _update_telescope_state_callback = self.update_telescope_state_callback,
            _update_telescope_health_state_callback = self.update_telescope_health_state_callback,
            _update_tmc_op_state_callback = self.update_tmc_op_state_callback,
            _update_subarray_health_state_callback = self.update_subarray_health_state_callback
        )
        cm.input_parameter.tm_dish_dev_names = []
        if not self.DishLeafNodePrefix == "":
            cm.input_parameter.tm_dish_dev_names = cm.add_dishes(self.DishLeafNodePrefix, self.NumDishes)

        cm.add_multiple_devices(self.TMMidSubarrayNodes)
        cm.input_parameter.tm_subarray_dev_names = self.TMMidSubarrayNodes
        cm.add_device(self.CspMasterFQDN)
        cm.input_parameter.csp_master_dev_name = self.CspMasterFQDN or ""
        cm.add_device(self.CspMasterLeafNodeFQDN)
        cm.input_parameter.tm_leaf_csp_master_dev_name = self.CspMasterLeafNodeFQDN or ""
        cm.add_device(self.SdpMasterFQDN)
        cm.input_parameter.sdp_master_dev_name = self.SdpMasterFQDN or ""
        cm.add_device(self.SdpMasterLeafNodeFQDN)
        cm.input_parameter.tm_leaf_sdp_master_dev_name = self.SdpMasterLeafNodeFQDN or ""
        cm.add_multiple_devices(self.TMMidCspSubarrayLeafNodes)
        cm.input_parameter.csp_subarray_dev_names = self.TMMidCspSubarrayLeafNodes
        cm.add_multiple_devices(self.TMMidSdpSubarrayLeafNodes)
        cm.input_parameter.sdp_subarray_dev_names = self.TMMidSdpSubarrayLeafNodes
        return cm

    def update_device_callback(self, devInfo):
        self.push_change_event("InternalModel", devInfo)
    
    def update_telescope_state_callback(self, telescope_state):
        self.push_change_event("telescopeState", telescope_state)
    
    def update_telescope_health_state_callback(self, telescope_health_state):
        self.push_change_event("telescopeHealthState", telescope_health_state)
    
    def update_tmc_op_state_callback(self, tmc_op_state):
        self.push_change_event("TMOpState", tmc_op_state)

    def update_subarray_health_state_callback(self, devInfo):
        if "1" in devInfo.dev_name:
            self.push_change_event("subarray1HealthState", devInfo.healthState)
        elif "2" in devInfo.dev_name:
            self.push_change_event("subarray2HealthState", devInfo.healthState)
        else:
            self.push_change_event("subarray3HealthState", devInfo.healthState)

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

            device.set_change_event("subarray1HealthState", True, True)
            device.set_change_event("subarray2HealthState", True, True)
            device.set_change_event("subarray3HealthState", True, True)
            device.set_change_event("telescopeHealthState", True, True)
            device.set_change_event("telescopeState", True, True)
            device.set_change_event("InternalModel", True, True)
            device.set_change_event("TMOpState", True, True)

            device.op_state_model.perform_action("component_on")
            device.component_manager.command_executor.add_command_execution("0", "Init", ResultCode.OK, "")
            return (ResultCode.OK, "")

    def always_executed_hook(self):
        # PROTECTED REGION ID(CentralNode.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CentralNode.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CentralNode.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  CentralNode.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_telescopeHealthState(self):
        # PROTECTED REGION ID(CentralNode.telescope_healthstate_read) ENABLED START #
        return self.component_manager.component.telescope_health_state
        # PROTECTED REGION END #    //  CentralNode.telescope_healthstate_read

    def read_subarray1HealthState(self):
        # PROTECTED REGION ID(CentralNode.subarray1_healthstate_read) ENABLED START #
        for dev_name in self.component_manager.input_parameter.tm_subarray_dev_names:
            if "1" in dev_name:
                return self.component_manager.get_device(dev_name).healthState
        return HealthState.UNKNOWN
        # PROTECTED REGION END #    //  CentralNode.subarray1_healthstate_read

    def read_subarray2HealthState(self):
        # PROTECTED REGION ID(CentralNode.subarray2_healthstate_read) ENABLED START #
        for dev_name in self.component_manager.input_parameter.tm_subarray_dev_names:
            if "2" in dev_name:
                return self.component_manager.get_device(dev_name).healthState
        return HealthState.UNKNOWN
        # PROTECTED REGION END #    //  CentralNode.subarray2_healthstate_read

    def read_subarray3HealthState(self):
        # PROTECTED REGION ID(CentralNode.subarray3HealthState_read) ENABLED START #
        for dev_name in self.component_manager.input_parameter.tm_subarray_dev_names:
            if "3" in dev_name:
                return self.component_manager.get_device(dev_name).healthState
        return HealthState.UNKNOWN
        # PROTECTED REGION END #    //  CentralNode.subarray3HealthState_read

    def read_telescopeState(self):
        # PROTECTED REGION ID(CentralNode.telescope_state_read) ENABLED START #
        return self.component_manager.component.telescope_state
        # PROTECTED REGION END #    //  CentralNode.telescope_state_read

    def read_imaging(self):
        # PROTECTED REGION ID(CentralNode.imaging_read) ENABLED START #
        return self.component_manager.component.imaging
        # PROTECTED REGION END #    //  CentralNode.imaging_read

    def read_pss(self):
        # PROTECTED REGION ID(CentralNode.PSS_read) ENABLED START #
        return self.component_manager.component.pss
        # PROTECTED REGION END #    //  CentralNode.PSS_read

    def read_pst(self):
        # PROTECTED REGION ID(CentralNode.PST_read) ENABLED START #
        return self.component_manager.component.pst
        # PROTECTED REGION END #    //  CentralNode.PST_read

    def read_vlbi(self):
        # PROTECTED REGION ID(CentralNode.VLBI_read) ENABLED START #
        return self.component_manager.component.vlbi
        # PROTECTED REGION END #    //  CentralNode.VLBI_read

    def read_desiredTelescopeState(self):
        # PROTECTED REGION ID(CentralNode.desired_telescope_state_read) ENABLED START #
        return self.component_manager.component.desired_telescope_state
        # PROTECTED REGION END #    //  CentralNode.desired_telescope_state_read

    def read_commandInProgress(self):
        # PROTECTED REGION ID(CentralNode.desired_telescope_state_read) ENABLED START #
        return self.component_manager.command_executor.command_in_progress
        # PROTECTED REGION END #    //  CentralNode.activity_message_read

    def read_InternalModel(self):
        # PROTECTED REGION ID(CentralNode.desired_telescope_state_read) ENABLED START #
        return json.dumps(self.component_manager.component.to_dict())
        # PROTECTED REGION END #    //  CentralNode.activity_message_read
    
    def read_CommandExecuted(self):
        # PROTECTED REGION ID(Counter.CommandExecuted_read) ENABLED START #
        """Return the CommandExecuted attribute."""
        result = []
        i = 0
        for command_executed in reversed(self.component_manager.command_executor.command_executed):
            if i == 100:
                break
            single_res = [str(command_executed["Id"]), str(command_executed["Command"]), str(command_executed["ResultCode"]), str(command_executed["Message"])]
            result.append(single_res)
            i += 1
        return result
        # PROTECTED REGION END #    //  Counter.CommandExecuted_read

    def read_CspMasterDevName(self):
        # PROTECTED REGION ID(Counter.CspMasterDevName_read) ENABLED START #
        """Return the CspMasterDevName attribute."""
        return self.component_manager.input_parameter.csp_master_dev_name
        # PROTECTED REGION END #    //  Counter.CspMasterDevName_read

    def write_CspMasterDevName(self, value):
        # PROTECTED REGION ID(Counter.CspMasterDevName_write) ENABLED START #
        """Set the CspMasterDevName attribute."""
        self.component_manager.input_parameter.csp_master_dev_name = value
        # PROTECTED REGION END #    //  Counter.CspMasterDevName_write

    def read_SdpMasterDevName(self):
        # PROTECTED REGION ID(Counter.SdpMasterDevName_read) ENABLED START #
        """Return the SdpMasterDevName attribute."""
        return self.component_manager.input_parameter.sdp_master_dev_name
        # PROTECTED REGION END #    //  Counter.SdpMasterDevName_read

    def write_SdpMasterDevName(self, value):
        # PROTECTED REGION ID(Counter.SdpMasterDevName_write) ENABLED START #
        """Set the SdpMasterDevName attribute."""
        self.component_manager.input_parameter.sdp_master_dev_name = value
        # PROTECTED REGION END #    //  Counter.SdpMasterDevName_write

    def read_LeafCspMasterDevName(self):
        # PROTECTED REGION ID(Counter.LeafCspMasterDevName_read) ENABLED START #
        """Return the LeafCspMasterDevName attribute."""
        return self.component_manager.input_parameter.tm_leaf_csp_master_dev_name
        # PROTECTED REGION END #    //  Counter.LeafCspMasterDevName_read

    def write_LeafCspMasterDevName(self, value):
        # PROTECTED REGION ID(Counter.LeafCspMasterDevName_write) ENABLED START #
        """Set the LeafCspMasterDevName attribute."""
        self.component_manager.input_parameter.tm_leaf_csp_master_dev_name = value
        # PROTECTED REGION END #    //  Counter.LeafCspMasterDevName_write

    def read_LeafSdpMasterDevName(self):
        # PROTECTED REGION ID(Counter.LeafSdpMasterDevName_read) ENABLED START #
        """Return the LeafSdpMasterDevName attribute."""
        return self.component_manager.input_parameter.tm_leaf_sdp_master_dev_name
        # PROTECTED REGION END #    //  Counter.LeafSdpMasterDevName_read

    def write_LeafSdpMasterDevName(self, value):
        # PROTECTED REGION ID(Counter.LeafSdpMasterDevName_write) ENABLED START #
        """Set the LeafSdpMasterDevName attribute."""
        self.component_manager.input_parameter.tm_leaf_sdp_master_dev_name = value
        # PROTECTED REGION END #    //  Counter.LeafSdpMasterDevName_write

    def read_TMOpState(self):
        # PROTECTED REGION ID(Counter.TMOpState_read) ENABLED START #
        """Return the TMOpState attribute."""
        return self.component_manager.component.tmc_op_state
        # PROTECTED REGION END #    //  Counter.TMOpState_read

    def read_SubarrayDevNames(self):
        # PROTECTED REGION ID(Counter.SubarrayDevNames_read) ENABLED START #
        """Return the SubarrayDevNames attribute."""
        return self.component_manager.input_parameter.tm_subarray_dev_names
        # PROTECTED REGION END #    //  Counter.SubarrayDevNames_read

    def write_SubarrayDevNames(self, value):
        # PROTECTED REGION ID(Counter.SubarrayDevNames_write) ENABLED START #
        """Set the SubarrayDevNames attribute."""
        self.component_manager.input_parameter.tm_subarray_dev_names = value
        # PROTECTED REGION END #    //  Counter.SubarrayDevNames_write

    def read_CspSubarrayDevNames(self):
        # PROTECTED REGION ID(Counter.CspSubarrayDevNames_read) ENABLED START #
        """Return the CspSubarrayDevNames attribute."""
        return self.component_manager.input_parameter.csp_subarray_dev_names
        # PROTECTED REGION END #    //  Counter.CspSubarrayDevNames_read

    def write_CspSubarrayDevNames(self, value):
        # PROTECTED REGION ID(Counter.CspSubarrayDevNames_write) ENABLED START #
        """Set the CspSubarrayDevNames attribute."""
        self.component_manager.input_parameter.csp_subarray_dev_names = value
        # PROTECTED REGION END #    //  Counter.CspSubarrayDevNames_write

    def read_SdpSubarrayDevNames(self):
        # PROTECTED REGION ID(Counter.SdpSubarrayDevNames_read) ENABLED START #
        """Return the SdpSubarrayDevNames attribute."""
        return self.component_manager.input_parameter.sdp_subarray_dev_names
        # PROTECTED REGION END #    //  Counter.SdpSubarrayDevNames_read

    def write_SdpSubarrayDevNames(self, value):
        # PROTECTED REGION ID(Counter.SdpSubarrayDevNames_write) ENABLED START #
        """Set the SdpSubarrayDevNames attribute."""
        self.component_manager.input_parameter.sdp_subarray_dev_names = value
        # PROTECTED REGION END #    //  Counter.SdpSubarrayDevNames_write

    def read_DishDevNames(self):
        # PROTECTED REGION ID(Counter.DishDevNames_read) ENABLED START #
        """Return the DishDevNames attribute."""
        return self.component_manager.input_parameter.tm_dish_dev_names
        # PROTECTED REGION END #    //  Counter.DishDevNames_read

    def write_DishDevNames(self, value):
        # PROTECTED REGION ID(Counter.DishDevNames_write) ENABLED START #
        """Set the DishDevNames attribute."""
        self.component_manager.input_parameter.tm_dish_dev_names = value
        # PROTECTED REGION END #    //  Counter.DishDevNames_write
    

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
        unique_id = self.component_manager.command_executor.enqueue_command(handler)
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
        unique_id = self.component_manager.command_executor.enqueue_command(handler)
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_StowAntennas_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("StowAntennas")
        return handler.check_allowed()

    @command(
        dtype_in=("str",),
        doc_in="List of Receptors to be stowed",
    )
    def StowAntennas(self, argin):
        """
        This command stows the specified receptors.
        """
        handler = self.get_command_object("StowAntennas")
        unique_id = self.component_manager.command_executor.enqueue_command(handler, argin)
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_TelescopeOff_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("TelescopeOff")
        return handler.check_allowed()

    @command()
    def TelescopeOff(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, Off() command 
        on CspMasterLeafNode and SdpMasterLeafNode.

        """
        handler = self.get_command_object("TelescopeOff")
        unique_id = self.component_manager.command_executor.enqueue_command(handler)
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_TelescopeOn_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("TelescopeOn")
        return handler.check_allowed()

    @command()
    @DebugIt()
    def TelescopeOn(self):
        """
        This command invokes TelescopeOn() command on DishLeadNode, CspMasterLeafNode,
        SdpMasterLeafNode.
        """
        handler = self.get_command_object("TelescopeOn")
        unique_id = self.component_manager.command_executor.enqueue_command(handler)
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_On_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        """
        handler = self.get_command_object("On")
        return handler.check_allowed()

    @command()   
    @DebugIt()
    def On(self):
        """
        This command invokes On command on DishLeadNode, TelescopeOn() command on CspMasterLeafNode,
        SdpMasterLeafNode.
        """
        handler = self.get_command_object("On")
        unique_id = self.component_manager.command_executor.enqueue_command(handler)
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
        dtype_out="str",
        doc_out="information-only string",
    )
    @DebugIt()
    def AssignResources(self, argin):
        """
        AssignResources command invokes the AssignResources command on lower level devices.
        """
        handler = self.get_command_object("AssignResources")
        unique_id = self.component_manager.command_executor.enqueue_command(handler, argin)
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
        dtype_out="str",
        doc_out="information-only string",
    )
    @DebugIt()
    def ReleaseResources(self, argin):
        """
        Release all the resources assigned to the given Subarray.
        """
        handler = self.get_command_object("ReleaseResources")
        unique_id = self.component_manager.command_executor.enqueue_command(handler, argin)
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Standby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("Standby")
        return handler.check_allowed()

    @command()
    @DebugIt()
    def Standby(self):
        """
        This command invokes Standby() command on CspMasterLeafNode,
        SdpMasterLeafNode and DishLeafNode.

        """
        handler = self.get_command_object("Standby")
        unique_id = self.component_manager.command_executor.enqueue_command(handler)
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_telescope_standby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        handler = self.get_command_object("TelescopeStandby")
        return handler.check_allowed()

    @command()
    @DebugIt()
    def TelescopeStandby(self):
        """
        This command invokes TelescopeStandby() command on CspMasterLeafNode,
        SdpMasterLeafNode and DishLeafNode.

        """
        handler = self.get_command_object("TelescopeStandby")
        unique_id = self.component_manager.command_executor.enqueue_command(handler)
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_Off_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        
        handler = self.get_command_object("Off")
        return handler.check_allowed()

    @command()
    def Off(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, 
        TelescopeOff() command on CspMasterLeafNode and
        SdpMasterLeafNode.

        """
        handler = self.get_command_object("Off")
        unique_id = self.component_manager.command_executor.enqueue_command(handler)
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        args = ()
        for (command_name, command_class) in [
            ("On", TelescopeOn),
            ("TelescopeOn", TelescopeOn),
            ("Off", TelescopeOff),
            ("TelescopeOff", TelescopeOff),
            ("StartUpTelescope", TelescopeOn),
            ("StandByTelescope", TelescopeOff),
            ("AssignResources", AssignResources),
            ("ReleaseResources", ReleaseResources),
            ("StowAntennas", StowAntennas),
            ("Standby", TelescopeStandby),
            ("TelescopeStandby", TelescopeStandby)
        ]:
            command_obj = command_class(self.component_manager, self.op_state_model, *args, self.logger)
            self.register_command_object(command_name, command_obj)

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(CentralNode.main) ENABLED START #
    """
    Runs the CentralNode.
    :param args: Arguments internal to TANGO

    :param kwargs: Arguments internal to TANGO

    :return: CentralNode TANGO object.
    """
    return run((CentralNode,), args=args, **kwargs)
    # PROTECTED REGION END #    //  CentralNode.main


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
#
# This file is part of the CentralNode project
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""
Central Node is a coordinator of the complete M&C system. Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
from logging import debug
import threading
from time import sleep
from ska_tango_base.base import component_manager
# Tango imports
from tango import DebugIt, AttrWriteType, DevState, DevString
from tango.server import run, attribute, command, device_property
from ska_tmc_centralnode_mid.manager.component_manager import CNComponentManager
from ska_tmc_centralnode_mid.model.op_state_model import TMCOpStateMachine, TMCOpStateModel
from tmc.common.tango_server_helper import TangoServerHelper

# Additional import
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from ska_tmc_centralnode_mid import const, release
from ska_tmc_centralnode_mid.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode_mid.commands.off_command import Off
from ska_tmc_centralnode_mid.commands.on_command import On
from ska_tmc_centralnode_mid.commands.telescope_on_command import TelescopeOn
from ska_tmc_centralnode_mid.commands.telescope_standby_command import TelescopeStandby
from ska_tmc_centralnode_mid.commands.assign_resources_command import AssignResources
from ska_tmc_centralnode_mid.commands.release_resources_command import ReleaseResources
from ska_tmc_centralnode_mid.commands.stow_antennas_command import StowAntennas
from ska_tmc_centralnode_mid.commands.standby_command import Standby
from ska_tmc_centralnode_mid.resource_manager import ResourceManager
from ska_tmc_centralnode_mid.device_data import DeviceData
from ska_tmc_centralnode_mid.obs_state_check import ObsStateAggregator
from ska_tmc_centralnode_mid.health_state_aggregator import HealthStateAggregator
from ska_tmc_centralnode_mid.const import ModesAvailability
from ska_tmc_centralnode_mid.op_state_aggregator import OpStateAggregator
from ska_tmc_centralnode_mid.telescope_state_aggregator import TelescopeStateAggregator
from ska_tmc_centralnode_mid.commands.startup_telescope_command import StartUpTelescope
from ska_tmc_centralnode_mid.commands.standby_telescope_command import StandByTelescope




# PROTECTED REGION END #    //  CentralNode.additional_import

__all__ = [
    "CentralNode",
    "main",
    "AssignResources",
    "DeviceData",
    "const",
    "ObsStateAggregator",
    "release",
    "ReleaseResources",
    "TelescopeOff",
    "StowAntennas",
    "Off",
    "TelescopeOn",
    "StowAntennas",
    "On",
    "Standby",
    "TelescopeStandby",
    "StandByTelescope",
    "StartUpTelescope"
]


class CentralNode(SKABaseDevice):
    """
    Central Node is a coordinator of the complete M&C system.

    :Device Properties:

        CentralAlarmHandler:
            Device name of CentralAlarmHandler

        TMAlarmHandler:
            Device name of TMAlarmHandler

        TMMidSubarrayNodes:
            List of TM Mid Subarray Node devices.

    :Device Attributes:

        telescopeHealthState:
            Health state of Telescope

        subarray1HealthState:
            Health state of SubarrayNode1

        subarray2HealthState:
            Health state of SubarrayNode2

        subarray3HealthState:
            Health state of SubarrayNode3

        activityMessage:
            String providing information about the current activity in Central Node.



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
        default_value=1,
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

    activityMessage = attribute(
        dtype="str",
        access=AttrWriteType.READ_WRITE,
        doc="Activity Message",
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

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger,
            callback=super()._update_state)
        cm =  CNComponentManager(
            self.op_state_model, logger=self.logger
        )
        cm.add_dishes(self.DishLeafNodePrefix, self.NumDishes)
        cm.add_multiple_devices(self.TMMidSubarrayNodes)
        cm.add_device(self.CspMasterFQDN)
        cm.add_device(self.SdpMasterFQDN)
        return cm

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

            :raises: DevFailed if error occurs while initializing the CentralNode device or if error occurs while
                    creating device proxy for any of the devices like SubarrayNode, DishLeafNode, CSPMasterLeafNode
                    or SDPMasterLeafNode.

            """
            super().do()

            device = self.target
            self.logger.info("Device initialisating...")
            # Get Instance of TangoServerHelper class 
            this_server = TangoServerHelper.get_instance()
            this_server.set_tango_class(device)
            device.attr_map = {}
            #Initilise the attributes
            device.attr_map["activityMessage"] = ""
            device.attr_map["subarray1HealthState"] = HealthState.UNKNOWN
            device.attr_map["subarray2HealthState"] = HealthState.UNKNOWN
            device.attr_map["subarray3HealthState"] = HealthState.UNKNOWN
            device.attr_map["telescopeHealthState"] = HealthState.UNKNOWN
            device.attr_map["telescopeState"] = DevState.STANDBY
            device.attr_map["desiredTelescopeState"] = None
            device.attr_map["commandInProgress"] = ""
            device.attr_map["imaging"] = ModesAvailability.not_available
            device.attr_map["pss"] = ModesAvailability.not_available
            device.attr_map["pst"] = ModesAvailability.not_available
            device.attr_map["vlbi"] = ModesAvailability.not_available
            device._health_state = HealthState.OK
            device._build_state = "{},{},{}".format(
                release.name, release.version, release.description
            )
            device._version_id = release.version
            device.device_data = DeviceData.get_instance()
            device.device_data.desired_telescope_state = {"TelescopeOn" : DevState.ON, "TelescopeStandby" : DevState.STANDBY, "TelescopeOff" : DevState.OFF}
            self.logger.debug(const.STR_INIT_SUCCESS)
            # Initialize resource manager instance and initialize the resource matrix with availabler resources
            # Note: ResourceManager's instance has to be initialised before ObsStateAggregator
            device.device_data.resource_manager = ResourceManager.get_instance()
            device.device_data.resource_manager.initialize_resource_matrix(device.DishLeafNodePrefix, device.NumDishes)

            # Initialization of ObsState aggregator object and start obs state aggregation
            device.device_data.obs_state_aggregator = ObsStateAggregator(
                device.TMMidSubarrayNodes, self.logger
            )
            device.device_data.obs_state_aggregator.start_aggregation()
            
            
            #create healthStateAggregator object and start health state aggregation
            device.device_data.health_aggreegator = HealthStateAggregator(self.logger)
            device.device_data.health_aggreegator.subscribe_event()

            #create TelescopeStateAggregator object and start telescope state aggregation
            try:
                device.device_data.telescope_state_aggregator = TelescopeStateAggregator(self.logger)
                device.device_data.telescope_state_aggregator.subscribe_event() 
                device.device_data.telescope_state_aggregator.start_telescope_state_aggregation()
            except Exception as e:
                self.logger.error(f"Exception in TelescopeStateAggregation {e}")
            #create OpStateAggregator object and start state aggregation
            try:
                device.device_data.state_aggregator = OpStateAggregator(self.logger)
                device.device_data.state_aggregator.subscribe_event() 
                device.device_data.state_aggregator.start_state_aggregation()
            except Exception as e:
                self.logger.error(f"Exception in OpState Aggregation {e}")
            
            for subarray in range(0, len(device.TMMidSubarrayNodes)):
                tokens = device.TMMidSubarrayNodes[subarray].split("/")
                subarrayID = int(tokens[2])
                # The below code appends the FQDN corresponding to each subarray Id into the dictionary.
                # This is required in AssignResource command where according to Subarray Id in input json, proxy has to be created.
                device.device_data.subarray_FQDN_dict[
                    subarrayID
                ] = device.TMMidSubarrayNodes[subarray]
            
            # Method to check CentralNode device State
            # device.check_cn_state()

            device.op_state_model.perform_action("component_on")
            
            this_server.write_attr("activityMessage", const.STR_INIT_SUCCESS, False)
            self.logger.info(const.STR_INIT_SUCCESS)
            return (ResultCode.OK, device.attr_map["activityMessage"])


    def always_executed_hook(self):
        # PROTECTED REGION ID(CentralNode.always_executed_hook) ENABLED START #
        """ Internal construct of TANGO. """
        # PROTECTED REGION END #    //  CentralNode.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(CentralNode.delete_device) ENABLED START #
        """ Internal construct of TANGO. """
        # PROTECTED REGION END #    //  CentralNode.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_telescopeHealthState(self):
        # PROTECTED REGION ID(CentralNode.telescope_healthstate_read) ENABLED START #
        """ Internal construct of TANGO. Returns the Telescope health state."""
        return self.attr_map["telescopeHealthState"]
        # PROTECTED REGION END #    //  CentralNode.telescope_healthstate_read

    def read_subarray1HealthState(self):
        # PROTECTED REGION ID(CentralNode.subarray1_healthstate_read) ENABLED START #
        """ Internal construct of TANGO. Returns Subarray1 health state. """
        return self.attr_map["subarray1HealthState"]
        # PROTECTED REGION END #    //  CentralNode.subarray1_healthstate_read

    def read_subarray2HealthState(self):
        # PROTECTED REGION ID(CentralNode.subarray2_healthstate_read) ENABLED START #
        """ Internal construct of TANGO. Returns Subarray2 health state. """
        return self.attr_map["subarray2HealthState"]

        # PROTECTED REGION END #    //  CentralNode.subarray2_healthstate_read

    def read_subarray3HealthState(self):
        # PROTECTED REGION ID(CentralNode.subarray3HealthState_read) ENABLED START #
        """ Internal construct of TANGO. Returns Subarray3 health state. """
        return self.attr_map["subarray3HealthState"]

        # PROTECTED REGION END #    //  CentralNode.subarray3HealthState_read

    def read_activityMessage(self):
        # PROTECTED REGION ID(CentralNode.activity_message_read) ENABLED START #
        """Internal construct of TANGO. Returns activity message. """
        return self.attr_map["activityMessage"]
        # PROTECTED REGION END #    //  CentralNode.activity_message_read

    def write_activityMessage(self, value):
        # PROTECTED REGION ID(CentralNode.activity_message_write) ENABLED START #
        """Internal construct of TANGO. Sets the activity message. """
        self.update_attr_map("activityMessage", value)
        # PROTECTED REGION END #    //  CentralNode.activity_message_write

    def read_telescopeState(self):
        # PROTECTED REGION ID(CentralNode.telescope_state_read) ENABLED START #
        """Internal construct of TANGO. Returns Telescope State. """
        return self.attr_map["telescopeState"]
        # PROTECTED REGION END #    //  CentralNode.telescope_state_read

    def read_imaging(self):
        # PROTECTED REGION ID(CentralNode.imaging_read) ENABLED START #
        """Internal construct of TANGO. Returns imaging. """
        return self.attr_map["imaging"]
        # PROTECTED REGION END #    //  CentralNode.imaging_read

    def read_pss(self):
        # PROTECTED REGION ID(CentralNode.PSS_read) ENABLED START #
        """Internal construct of TANGO. Returns PSS. """
        return self.attr_map["pss"]
        # PROTECTED REGION END #    //  CentralNode.PSS_read

    def read_pst(self):
        # PROTECTED REGION ID(CentralNode.PST_read) ENABLED START #
        """Internal construct of TANGO. Returns PST """
        return self.attr_map["pst"]
        # PROTECTED REGION END #    //  CentralNode.PST_read

    def read_vlbi(self):
        # PROTECTED REGION ID(CentralNode.VLBI_read) ENABLED START #
        """Internal construct of TANGO. Returns VLBI State. """
        return self.attr_map["vlbi"]
        # PROTECTED REGION END #    //  CentralNode.VLBI_read

    def read_desiredTelescopeState(self):
        # PROTECTED REGION ID(CentralNode.desired_telescope_state_read) ENABLED START #
        """Internal construct of TANGO. Returns Desired Telescope State. """
        return self.attr_map["desiredTelescopeState"]

    def read_commandInProgress(self):
        # PROTECTED REGION ID(CentralNode.desired_telescope_state_read) ENABLED START #
        """Internal construct of TANGO. Returns commandInProgress Telescope State. """
        return self.attr_map["commandInProgress"]
        # PROTECTED REGION END #    //  CentralNode.activity_message_read

    def update_attr_map(self, attr, val):
        """
        This method updates attribute value in attribute map. Once a thread has acquired a lock,
        subsequent attempts to acquire it are blocked, until it is released.
        """
        lock = threading.Lock()
        lock.acquire()
        self.attr_map[attr] = val
        lock.release()
    
    # def check_cn_state(self):
    #     """
    #     This method creates and start thread to check CentralNode device State
    #     """
    #     try:
    #         # Create event for state change
    #         self._cn_state_event = threading.Event()  # thread control
    #         # create thread
    #         self.logger.info("Starting thread to check the state of CentralNode.")
    #         cn_state_thread = threading.Thread(
    #             target=self.monitor_cn_state,
    #         )
    #         cn_state_thread.start() 
    #     except Exception as e:
    #         self.logger.exception(f"In check_cn_state exception is:{e}")
    
    # def monitor_cn_state(self):
    #     """
    #     This methods monitors the State of CentralNode, once state of CentralNode is OFF and state of all TMC devices is OFF,
    #     TMC On command is getting invoked which makes CentralNode device State to ON
    #     """
    #     self.logger.info("Started monitoring CN state")
    #     this_server = TangoServerHelper.get_instance()
    #     device_data = DeviceData.get_instance()
    #     try:
    #         while not self._cn_state_event.isSet():
    #             cn_state = this_server.get_state()
    #             # CentralNode can be OFF after init and will be updated to UNKNOWN until receives states from all TMC devices
    #             if cn_state in [DevState.OFF, DevState.UNKNOWN] and device_data._tmc_off_trigger.isSet():
    #                 self.logger.info(
    #                             f"CN_device_states is:{cn_state}"
    #                         )
    #                 # Time sleep added to wait for On() command to be registered using init_register_command() method
    #                 sleep(1)
    #                 this_server.device.On()
    #                 self.logger.info(
    #                             f"On command is called"
    #                         )
    #                 self.logger.info(
    #                             f"CN_device_states is:{cn_state}"
    #                         )
    #                 device_data._tmc_off_trigger.clear()
    #                 break

    #     except Exception as e:
    #         self.logger.exception(f"In monitor_cn_state exception is:{e}")

    # --------
    # Commands
    # --------

    # pylint: disable=unused-variable

    # pylint: enable=unused-variable

    def is_StartUpTelescope_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

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
        This command invokes SetOperateMode() command on DishLeadNode, On() command on CspMasterLeafNode,
        SdpMasterLeafNode and SubarrayNode and sets the Central Node into ON state.
        """
        handler = self.get_command_object("StartUpTelescope")
        (result_code, message) = handler()
        return [[result_code], [message]]

    def is_StandByTelescope_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

        """
        handler = self.get_command_object("StandByTelescope")
        return handler.check_allowed()

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="[ResultCode, information-only string]",
    )
    def StandByTelescope(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, StandBy() command on CspMasterLeafNode and
        SdpMasterLeafNode and Off() command on SubarrayNode and sets CentralNode into OFF state.

        """
        handler = self.get_command_object("StandByTelescope")
        (result_code, message) = handler()
        return [[result_code], [message]]

    def is_StowAntennas_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

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
        handler(argin)

    def is_TelescopeOff_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

        """
        handler = self.get_command_object("TelescopeOff")
        return handler.check_allowed()

    @command()
    def TelescopeOff(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, Off() command on CspMasterLeafNode and
        SdpMasterLeafNode sets CentralNode into OFF state.

        """
        handler = self.get_command_object("TelescopeOff")
        handler()

    def is_TelescopeOn_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

        """
        handler = self.get_command_object("TelescopeOn")
        return handler.check_allowed()

    @command()
    @DebugIt()
    def TelescopeOn(self):
        """
        This command invokes TelescopeOn() command on DishLeadNode, CspMasterLeafNode,
        SdpMasterLeafNode .
        """
        handler = self.get_command_object("TelescopeOn")
        handler()

    def is_On_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

        """
        handler = self.get_command_object("On")
        return handler.check_allowed()

    @command()   
    @DebugIt()
    def On(self):
        """
        This command invokes On command on DishLeadNode, On() command on CspMasterLeafNode,
        SdpMasterLeafNode and sets the Central Node into ON state.
        This commmand turn On the TMC devices
        """
        handler = self.get_command_object("On")
        handler()

    def is_AssignResources_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state

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
        message = handler(argin)
        return message

    def is_ReleaseResources_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state

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

        message = handler(argin)
        return message

    def is_Standby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

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
        handler()

    def is_telescope_standby_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

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
        handler()

    def is_Off_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run in current device state.

        """
        
        handler = self.get_command_object("Off")
        return handler.check_allowed()

    @command()
    def Off(self):
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, Off() command on CspMasterLeafNode and
        SdpMasterLeafNode and sets CentralNode into OFF state.

        """
        handler = self.get_command_object("Off")
        handler()

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        args = (self.device_data, self.op_state_model)
        self.on_object = On(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.register_command_object("On", self.on_object)
        self.telescope_on_object = TelescopeOn(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.register_command_object("TelescopeOn", self.telescope_on_object)
        self.telescope_off_object = TelescopeOff(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.off_object = Off(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.startup_object = StartUpTelescope(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.register_command_object("StartUpTelescope", self.startup_object)
        self.standby_object = StandByTelescope(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.register_command_object("StandByTelescope", self.standby_object)
        self.assign_object = AssignResources(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.release_object = ReleaseResources(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.stow_object = StowAntennas(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.standby_tmc_object = Standby(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.telescope_standby_object = TelescopeStandby(self.component_manager, self.op_state_model, *args, logger=self.logger)
        self.register_command_object("Off", self.off_object)
        self.register_command_object("AssignResources", self.assign_object)
        self.register_command_object("StowAntennas", self.stow_object)
        self.register_command_object("TelescopeOff", self.telescope_off_object)
        self.register_command_object("ReleaseResources", self.release_object)
        self.register_command_object("Standby", self.standby_tmc_object)
        self.register_command_object("TelescopeStandby", self.telescope_standby_object)
        

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

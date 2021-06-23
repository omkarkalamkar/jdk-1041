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
import threading
# Tango imports
from tango import DebugIt, AttrWriteType
from tango.server import run, attribute, command, device_property
from tmc.common.tango_server_helper import TangoServerHelper

# Additional import
from ska.base import SKABaseDevice
from ska.base.commands import ResultCode
from ska.base.control_model import HealthState
from tmc.centralnode import const, release
from tmc.centralnode.start_up_telescope_command import StartUpTelescope
from tmc.centralnode.stand_by_telescope_command import StandByTelescope
from tmc.centralnode.assign_resources_command import AssignResources
from tmc.centralnode.release_resources_command import ReleaseResources
from tmc.centralnode.stow_antennas_command import StowAntennas
from tmc.centralnode.standby_command import Standby
from tmc.centralnode.resource_manager import ResourceManager
from tmc.centralnode.device_data import DeviceData
from tmc.centralnode.obs_state_check import ObsStateAggregator
from tmc.centralnode.health_state_aggregator import HealthStateAggregator

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
    "StandByTelescope",
    "StartUpTelescope",
    "StowAntennas",
    "Standby"
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

    CspMasterLeafNodeFQDN = device_property(dtype="str")

    SdpMasterLeafNodeFQDN = device_property(dtype="str")

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

            device._health_state = HealthState.OK
            device._build_state = "{},{},{}".format(
                release.name, release.version, release.description
            )
            device._version_id = release.version
            device.device_data = DeviceData.get_instance()

            self.logger.debug(const.STR_INIT_SUCCESS)
            # Initialization of ObsState aggregator object and start obs state aggregation
            device.device_data.obs_state_aggregator = ObsStateAggregator(
                device.TMMidSubarrayNodes, self.logger
            )
            device.device_data.obs_state_aggregator.start_aggregation()
            
            # Initialize resource manager instance and initialize the resource matrix with availabler resources
            device.device_data.resource_manager = ResourceManager.get_instance()
            device.device_data.resource_manager.initialize_resource_matrix(device.DishLeafNodePrefix, device.NumDishes)

            #create healthStateAggregator object and start health state aggregation
            device.device_data.health_aggreegator = HealthStateAggregator(self.logger)
            device.device_data.health_aggreegator.subscribe_event()


            for subarray in range(0, len(device.TMMidSubarrayNodes)):
                tokens = device.TMMidSubarrayNodes[subarray].split("/")
                subarrayID = int(tokens[2])
                # The below code appends the FQDN corresponding to each subarray Id into the dictionary.
                # This is required in AssignResource command where according to Subarray Id in input json, proxy has to be created.
                device.device_data.subarray_FQDN_dict[
                    subarrayID
                ] = device.TMMidSubarrayNodes[subarray]
                
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
    
    def update_attr_map(self, attr, val):
        """
        This method updates attribute value in attribute map. Once a thread has acquired a lock,
        subsequent attempts to acquire it are blocked, until it is released.
        """
        lock = threading.Lock()
        lock.acquire()
        self.attr_map[attr] = val
        lock.release()
 
    # --------
    # Commands
    # --------

    # pylint: disable=unused-variable

    # pylint: enable=unused-variable

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
        "DevShort\ndish: JSON object consisting\n- receptorIDList: DevVarStringArray. "
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
        "releaseALL boolean as true and receptorIDList.",
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

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        args = (self.device_data, self.state_model, self.logger)
        self.startup_object = StartUpTelescope(*args)
        self.standby_object = StandByTelescope(*args)
        self.assign_object = AssignResources(*args)
        self.release_object = ReleaseResources(*args)
        self.stow_object = StowAntennas(*args)
        self.standby_tmc_object = Standby(*args)
        self.register_command_object("AssignResources", self.assign_object)
        self.register_command_object("StowAntennas", self.stow_object)
        self.register_command_object("StartUpTelescope", self.startup_object)
        self.register_command_object("StandByTelescope", self.standby_object)
        self.register_command_object("ReleaseResources", self.release_object)
        self.register_command_object("Standby", self.standby_tmc_object)


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

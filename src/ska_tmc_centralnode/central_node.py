"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
import json

import pandas as pd
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import HealthState
from ska_tmc_common.op_state_model import TMCOpStateModel
from ska_tmc_common.tmc_base_device import TMCBaseDevice
from tango import AttrWriteType, DebugIt
from tango.server import attribute, command, device_property

from ska_tmc_centralnode import release
from ska_tmc_centralnode.manager.component_manager import CNComponentManager
from ska_tmc_centralnode.model.input import InputParameterMid


class AbstractCentralNode(TMCBaseDevice):
    """
    Central Node is a coordinator of the complete Telescope system.
    Central Node is inherited from TMCBaseDevice class which is further inherited
    from SKABaseDevice class. TMCBaseDevice class contains attributes common
    to CentralNode and SubarrayNode.
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
    # ----------
    # Attributes
    # ----------

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

    def update_device_callback(self, devInfo):
        self._LastDeviceInfoChanged = devInfo.to_json()
        self.push_change_event("lastDeviceInfoChanged", devInfo.to_json())

    def update_telescope_state_callback(self, telescope_state):
        self.logger.info("telescopeState %s", telescope_state)
        self.push_change_event("telescopeState", telescope_state)

    def update_telescope_health_state_callback(self, telescope_health_state):
        self.push_change_event("telescopeHealthState", telescope_health_state)

    def update_tmc_op_state_callback(self, tmc_op_state):
        self.push_change_event("tmOpState", tmc_op_state)

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

            :return: A tuple containing a return code and a string message indicating status.
             The message is for information purpose only.

            :rtype: (ReturnCode, str)
            """
            super().do()

            self._device._build_state = "{},{},{}".format(
                release.name, release.version, release.description
            )
            self._device._version_id = release.version
            self._device._LastDeviceInfoChanged = ""
            self._device.set_change_event("telescopeHealthState", True, False)
            self._device.set_change_event("telescopeState", True, False)
            self._device.set_change_event("LastDeviceInfoChanged", True, False)
            self._device.set_change_event("tmOpState", True, False)
            self._device.op_state_model.perform_action("component_on")
            return (ResultCode.OK, "")

    def always_executed_hook(self):
        pass

    def delete_device(self):
        # if the init is called more than once
        # I need to stop all threads
        if hasattr(self, "component_manager"):
            self.component_manager.stop()

    def log_state(self, msg="Device States"):
        device_names = [
            device.to_dict()["dev_name"]
            for device in self.component_manager.devices
        ]
        dev_states = [
            device.to_dict()["state"]
            for device in self.component_manager.devices
        ]
        device_states = pd.DataFrame(
            {"Devices": device_names, "STATE": dev_states}
        )
        self.logger.info("\n" + msg + "\n" + device_states.to_string() + "\n")

    # ------------------
    # Attributes methods
    # ------------------

    def read_telescopeHealthState(self):
        return self.component_manager.component.telescope_health_state

    def read_telescopeState(self):
        return self.component_manager.component.telescope_state

    def read_desiredTelescopeState(self):
        return self.component_manager.component.desired_telescope_state

    def transformedInternalModel_read(self):
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
        return self.component_manager.input_parameter.tm_subarray_dev_names

    def write_subarrayDevNames(self, value):
        """Set the subarrayDevNames attribute."""
        self.component_manager.input_parameter.tm_subarray_dev_names = value
        self.component_manager.update_input_parameter()

    # --------
    # Commands
    # --------

    def is_TelescopeOn_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("TelescopeOn")

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def TelescopeOn(self):
        """
        This command invokes TelescopeOn() command on DishLeadNode, CspMasterLeafNode,
        SdpMasterLeafNode.
        """
        handler = self.get_command_object("TelescopeOn")
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    # TODO: Refactor below commands as a part of separate command refactoring
    # def is_StartUpTelescope_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current device state.

    #     :return: True if this command is allowed to be run in current device state.

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
    #     TelescopeOn() command on CspMasterLeafNode, SdpMasterLeafNode and SubarrayNode
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
    #     Checks whether this command is allowed to be run in current device state.

    #     :return: True if this command is allowed to be run in current device state.

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
    #     This command invokes SetStandbyLPMode() command on DishLeafNode, TelescopeStandBy() command
    #     on CspMasterLeafNode and SdpMasterLeafNode and TelescopeOff() command
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

    # def is_TelescopeOff_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current device state.

    #     :return: True if this command is allowed to be run in current device state.

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("TelescopeOff")
    #     return handler.check_allowed()

    # @command(dtype_out="DevVarLongStringArray")
    # def TelescopeOff(self):
    #     """
    #     This command invokes SetStandbyLPMode() command on DishLeafNode, Off() command
    #     on CspMasterLeafNode and SdpMasterLeafNode.

    #     """
    #     self.log_state("Device states before executing Telescope Off command")
    #     handler = self.get_command_object("TelescopeOff")
    #     if self.component_manager.command_executor.queue_full:
    #         return [[ResultCode.FAILED], ["Queue is full!"]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     self.log_state("Device states after executing Telescope Off command")
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    def is_On_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state.

        :rtype: boolean

        """
        return self.component_manager.is_command_allowed("On")

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
        result_code, unique_id = handler()
        return [[result_code], [str(unique_id)]]

    def is_AssignResources_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state.

        :return: True if this command is allowed to be run in current device state

        :rtype: boolean
        """
        return self.component_manager.is_command_allowed("AssignResources")

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
        self.log_state(
            "Device states before executing AssignResources command"
        )
        handler = self.get_command_object("AssignResources")
        args = json.loads(argin)
        result_code, unique_id = handler(args)
        self.log_state("Device states after executing AssignResources command")
        return [[result_code], [str(unique_id)]]

    # TODO: Refactor below commands as a part of separate command refactoring
    # def is_ReleaseResources_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current device state.

    #     :return: True if this command is allowed to be run in current device state.

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("ReleaseResources")
    #     return handler.check_allowed()

    # @command(
    #     dtype_in="str",
    #     doc_in="The string in JSON format. The JSON contains following values:\nsubarrayID: "
    #     "releaseALL boolean as true and receptor_ids.",
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="information-only string",
    # )
    # @DebugIt()
    # def ReleaseResources(self, argin):
    #     """
    #     Release all the resources assigned to the given Subarray.
    #     """
    #     self.log_state(
    #         "Device states before executing ReleaseResources command"
    #     )
    #     handler = self.get_command_object("ReleaseResources")
    #     if self.component_manager.command_executor.queue_full:
    #         return [[ResultCode.FAILED], ["Queue is full!"]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler, argin
    #     )
    #     self.log_state(
    #         "Device states after executing ReleaseResources command"
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_Standby_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current device state.

    #     :return: True if this command is allowed to be run in current device state.

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("Standby")
    #     return handler.check_allowed()

    # @command(
    #     dtype_out="DevVarLongStringArray",
    # )
    # @DebugIt()
    # def Standby(self):
    #     """
    #     This command invokes Standby() command on CspMasterLeafNode,
    #     SdpMasterLeafNode and DishLeafNode.

    #     """
    #     self.log_state("Device states before executing Standby command")
    #     handler = self.get_command_object("Standby")
    #     if self.component_manager.command_executor.queue_full:
    #         return [[ResultCode.FAILED], ["Queue is full!"]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     self.log_state("Device states after executing Standby command")
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_TelescopeStandby_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current device state.

    #     :return: True if this command is allowed to be run in current device state.

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("TelescopeStandby")
    #     return handler.check_allowed()

    # @command(
    #     dtype_out="DevVarLongStringArray",
    # )
    # @DebugIt()
    # def TelescopeStandby(self):
    #     """
    #     This command invokes TelescopeStandby() command on CspMasterLeafNode,
    #     SdpMasterLeafNode and DishLeafNode.

    #     """
    #     self.log_state(
    #         "Device states before executing Telescope Standby command"
    #     )
    #     handler = self.get_command_object("TelescopeStandby")
    #     if self.component_manager.command_executor.queue_full:
    #         return [[ResultCode.FAILED], ["Queue is full!"]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     self.log_state(
    #         "Device states after executing Telescope Standby command"
    #     )
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # def is_Off_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current device state.

    #     :return: True if this command is allowed to be run in current device state.

    #     :rtype: boolean
    #     """

    #     handler = self.get_command_object("Off")
    #     return handler.check_allowed()

    # @command(
    #     dtype_out="DevVarLongStringArray",
    # )
    # def Off(self):
    #     """
    #     This command invokes SetStandbyLPMode() command on DishLeafNode,
    #     TelescopeOff() command on CspMasterLeafNode and
    #     SdpMasterLeafNode.

    #     """
    #     self.log_state("Device states before executing Off command")
    #     handler = self.get_command_object("Off")
    #     if self.component_manager.command_executor.queue_full:
    #         return [[ResultCode.FAILED], ["Queue is full!"]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler
    #     )
    #     self.log_state("Device states after executing Off command")
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    # default ska mid
    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManager(
            self.op_state_model,
            _input_parameter=InputParameterMid(None),
            logger=self.logger,
            _update_device_callback=self.update_device_callback,
            _update_telescope_state_callback=self.update_telescope_state_callback,
            _update_telescope_health_state_callback=self.update_telescope_health_state_callback,
            _update_tmc_op_state_callback=self.update_tmc_op_state_callback,
            _update_imaging_callback=self.update_imaging_callback,
            communication_state_changed_callback=None,
            component_state_changed_callback=None,
            max_workers=self.MaxWorkerMonitoringLoop,
            proxy_timeout=self.ProxyTimeoutMonitoringLoop,
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

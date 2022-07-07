"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
from ska_ser_skuid.client import SkuidClient
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from tango import AttrWriteType
from tango.server import attribute, command, device_property, run

from ska_tmc_centralnode.central_node import AbstractCentralNode
from ska_tmc_centralnode.commands.assign_resources_command import (
    AssignResources,
)
from ska_tmc_centralnode.commands.release_resources_command import (
    ReleaseResources,
)

# from ska_tmc_centralnode.commands.stow_antennas_command import StowAntennas
# from ska_tmc_centralnode.commands.telescope_off_command import TelescopeOff
from ska_tmc_centralnode.commands.telescope_on_command import TelescopeOn

# from ska_tmc_centralnode.commands.telescope_standby_command import (
#     TelescopeStandby,
# )
from ska_tmc_centralnode.model.enum import ModesAvailability

__all__ = ["CentralNodeMid", "main"]


class CentralNodeMid(AbstractCentralNode):
    """
    Central Node is a coordinator of the complete Telescope system

    """

    # -----------------
    # Device Properties
    # -----------------
    NumDishes = device_property(
        dtype="uint",
        default_value=0,
        doc="Number of Dishes",
    )

    DishLeafNodePrefix = device_property(
        dtype="str",
        default_value="",
        doc="Device name prefix for Dish Leaf Node",
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

    SkuidServiceNamePort = device_property(
        dtype="DevString",
        default_value="ska-ser-skuid-test-svc.tmcmid.svc.cluster.local:9870",
    )
    # ----------
    # Attributes
    # ----------

    imaging = attribute(
        dtype=ModesAvailability,
        access=AttrWriteType.READ,
        doc="Imaging Attribute",
    )

    pss = attribute(
        dtype=ModesAvailability, access=AttrWriteType.READ, doc="PSS Attribute"
    )

    pst = attribute(
        dtype=ModesAvailability, access=AttrWriteType.READ, doc="PST Attribute"
    )

    vlbi = attribute(
        dtype=ModesAvailability,
        access=AttrWriteType.READ,
        doc="VLBI Attribute",
    )

    cspMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    sdpMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    leafCspMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    leafSdpMasterDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    cspSubarrayDevNames = attribute(
        dtype=("DevString",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=16,
    )

    sdpSubarrayDevNames = attribute(
        dtype=("DevString",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=16,
    )

    dishDevNames = attribute(
        dtype=("DevString",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=100,
    )

    tmLeafDishDevNames = attribute(
        dtype=("DevString",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=100,
    )

    def update_imaging_callback(self, imaging):
        self.logger.info("imaging %s", imaging)
        self.push_change_event("imaging", imaging)

    # ---------------
    # General methods
    # ---------------
    class InitCommand(AbstractCentralNode.InitCommand):
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
            # super().do()
            device=self._device

            device.set_change_event("imaging", True, False)

            return (ResultCode.OK, "")

    # ------------------
    # Attributes methods
    # ------------------

    def read_imaging(self):
        return self.component_manager.component.imaging

    def read_pss(self):
        return self.component_manager.component.pss

    def read_pst(self):
        return self.component_manager.component.pst

    def read_vlbi(self):
        return self.component_manager.component.vlbi

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

    def read_leafCspMasterDevName(self):
        """Return the leafcspMasterDevName attribute."""
        return (
            self.component_manager.input_parameter.tm_leaf_csp_master_dev_name
        )

    def write_leafCspMasterDevName(self, value):
        """Set the leafcspMasterDevName attribute."""
        self.component_manager.input_parameter.tm_leaf_csp_master_dev_name = (
            value
        )
        self.component_manager.update_input_parameter()

    def read_leafSdpMasterDevName(self):
        """Return the leafsdpMasterDevName attribute."""
        return (
            self.component_manager.input_parameter.tm_leaf_sdp_master_dev_name
        )

    def write_leafSdpMasterDevName(self, value):
        """Set the leafsdpMasterDevName attribute."""
        self.component_manager.input_parameter.tm_leaf_sdp_master_dev_name = (
            value
        )
        self.component_manager.update_input_parameter()

    def read_cspSubarrayDevNames(self):
        """Return the cspsubarraydevnames attribute."""
        return self.component_manager.input_parameter.csp_subarray_dev_names

    def write_cspSubarrayDevNames(self, value):
        """Set the cspsubarraydevnames attribute."""
        self.component_manager.input_parameter.csp_subarray_dev_names = value
        self.component_manager.update_input_parameter()

    def read_sdpSubarrayDevNames(self):
        """Return the sdpsubarraydevnames attribute."""
        return self.component_manager.input_parameter.sdp_subarray_dev_names

    def write_sdpSubarrayDevNames(self, value):
        """Set the sdpsubarraydevnames attribute."""
        self.component_manager.input_parameter.sdp_subarray_dev_names = value
        self.component_manager.update_input_parameter()

    def read_dishDevNames(self):
        """Return the dishdevnames attribute."""
        return self.component_manager.input_parameter.dish_dev_names

    def write_dishDevNames(self, value):
        """Set the dishdevnames attribute."""
        self.component_manager.input_parameter.dish_dev_names = value
        self.component_manager.update_input_parameter()

    def read_tmLeafDishDevNames(self):
        """Return the tmleafdishdevnames attribute."""
        return self.component_manager.input_parameter.tm_dish_dev_names

    def write_tmLeafDishDevNames(self, value):
        """Set the tmleafdishdevnames attribute."""
        self.component_manager.input_parameter.tm_dish_dev_names = value
        self.component_manager.update_input_parameter()

    # --------
    # Commands
    # --------
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
        dtype_out="DevVarLongStringArray",
    )
    def StowAntennas(self, argin):
        """
        This command stows the specified receptors.
        """
        self.log_state("Device states before executing StowAntennas command")
        handler = self.get_command_object("StowAntennas")
        if self.component_manager.command_executor.queue_full:
            return [[ResultCode.FAILED], ["Queue is full!"]]
        unique_id = self.component_manager.command_executor.enqueue_command(
            handler, argin
        )
        self.log_state("Device states after executing StowAntennas command")
        return [[ResultCode.QUEUED], [str(unique_id)]]

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()
        args = ()
        for (command_name, method_name) in [("TelescopeOn", "telescope_on")]:
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

            # command_obj = command_class(
            #     self.component_manager,
            #     self.op_state_model,
            #     *args,
            #     logger=self.logger,
            # )
        #     self.register_command_object(command_name, command_obj)
        # assign_resources_obj = AssignResources(
        #     self.component_manager,
        #     self.op_state_model,
        #     skuid=SkuidClient(skuid_url=self.SkuidServiceNamePort),
        #     *args,
        #     logger=self.logger,
        # )
        # self.register_command_object("AssignResources", assign_resources_obj)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """
    Runs the CentralNode.
    :param args: Arguments internal to TANGO

    :param kwargs: Arguments internal to TANGO

    :return: CentralNode TANGO object.
    """
    return run((CentralNodeMid,), args=args, **kwargs)


if __name__ == "__main__":
    main()

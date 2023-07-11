"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""
from ska_tango_base.commands import ResultCode
from ska_tmc_common.op_state_model import TMCOpStateModel
from tango import AttrWriteType
from tango.server import attribute, device_property, run

from ska_tmc_centralnode.central_node import AbstractCentralNode
from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.enum import ModesAvailability
from ska_tmc_centralnode.model.input import InputParameterMid

__all__ = ["CentralNodeMid", "main"]


class CentralNodeMid(AbstractCentralNode):
    """
    Central Node is a coordinator of the complete Telescope system

    """

    # -----------------
    # Device Properties
    # -----------------

    DishIDs = device_property(
        dtype=("str",),
        doc="List of the available dish ids",
        default_value=tuple(),
    )

    DishLeafNodePrefix = device_property(
        dtype="str",
        default_value="",
        doc="Device name prefix for Dish Leaf Node",
    )

    TMCMidCspSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of TM Mid CspSubarrayLeafNode devices",
        default_value=tuple(),
    )

    TMCMidSdpSubarrayLeafNodes = device_property(
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

    CspMasterLeafNodeDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    SdpMasterLeafNodeDevName = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
    )

    dishDevNames = attribute(
        dtype=("DevString",),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=100,
    )

    dishLeafNodeDevNames = attribute(
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
            super().do()

            self._device.set_change_event("imaging", True, False)

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

    def read_dishDevNames(self):
        """Return the dishdevnames attribute."""
        return self.component_manager.input_parameter.dish_dev_names

    def write_dishDevNames(self, value):
        """Set the dishdevnames attribute."""
        self.component_manager.input_parameter.dish_dev_names = value
        self.component_manager.update_input_parameter()

    def read_dishLeafNodeDevNames(self):
        """Return the dishLeafNodedevnames attribute."""
        return self.component_manager.input_parameter.dish_leaf_node_dev_names

    def write_dishLeafNodeDevNames(self, value):
        """Set the dishLeafNodedevnames attribute."""
        self.component_manager.input_parameter.dish_leaf_node_dev_names = value
        self.component_manager.update_input_parameter()

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

    # TODO: Not in the scope for PI15

    # --------
    # Commands
    # --------
    # def is_StowAntennas_allowed(self):
    #     """
    #     Checks whether this command is allowed to be run in current device state.

    #     :return: True if this command is allowed to be run in current device state.

    #     :rtype: boolean
    #     """
    #     handler = self.get_command_object("StowAntennas")
    #     return handler.check_allowed()

    # @command(
    #     dtype_in=("str",),
    #     doc_in="List of Receptors to be stowed",
    #     dtype_out="DevVarLongStringArray",
    # )
    # def StowAntennas(self, argin):
    #     """
    #     This command stows the specified receptors.
    #     """
    #     self.log_state("Device states before executing StowAntennas command")
    #     handler = self.get_command_object("StowAntennas")
    #     if self.component_manager.command_executor.queue_full:
    #         return [[ResultCode.FAILED], ["Queue is full!"]]
    #     unique_id = self.component_manager.command_executor.enqueue_command(
    #         handler, argin
    #     )
    #     self.log_state("Device states after executing StowAntennas command")
    #     return [[ResultCode.QUEUED], [str(unique_id)]]

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManagerMid(
            self.op_state_model,
            _input_parameter=InputParameterMid(None),
            logger=self.logger,
            _update_device_callback=self.update_device_callback,
            _update_telescope_state_callback=self.update_telescope_state_callback,
            _update_telescope_health_state_callback=self.update_telescope_health_state_callback,
            _update_tmc_op_state_callback=self.update_tmc_op_state_callback,
            _update_imaging_callback=self.update_imaging_callback,
            _telescope_availability_callback=self.update_telescope_availability_callback,
            communication_state_callback=None,
            component_state_callback=None,
            max_workers=self.MaxWorker,
            proxy_timeout=self.ProxyTimeout,
            sleep_time=self.SleepTime,
            skuid_service=self.SkuidService,
        )
        cm.input_parameter.dish_leaf_node_dev_names = []
        cm.input_parameter.dish_dev_names = []
        for dish in self.DishIDs:
            if "MKT" in dish:
                continue

            # For now generate FQDNs for SKA dishes only
            dish_id = dish[3:]
            cm.input_parameter.dish_leaf_node_dev_names.append(
                self.DishLeafNodePrefix + dish_id
            )
            cm.input_parameter.dish_dev_names.append(
                f"{'ska'}{dish_id}{'/dish/master'}"
            )
        cm.input_parameter.subarray_dev_names = self.TMCSubarrayNodes
        cm.input_parameter.csp_master_dev_name = self.CspMasterFQDN or ""
        cm.input_parameter.csp_mln_dev_name = self.CspMasterLeafNodeFQDN or ""
        cm.input_parameter.sdp_master_dev_name = self.SdpMasterFQDN or ""
        cm.input_parameter.sdp_mln_dev_name = self.SdpMasterLeafNodeFQDN or ""
        cm.input_parameter.csp_subarray_dev_names = (
            self.TMCMidCspSubarrayLeafNodes
        )
        cm.input_parameter.sdp_subarray_dev_names = (
            self.TMCMidSdpSubarrayLeafNodes
        )
        cm.input_parameter.dish_leaf_node_prefix = self.DishLeafNodePrefix

        cm.update_input_parameter()
        return cm

    def init_command_objects(self):
        """
        Initialises the command handlers for commands supported by this device.
        """
        super().init_command_objects()


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

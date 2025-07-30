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
from ska_tmc_centralnode.manager.component_manager_low import (
    CNComponentManagerLow,
)
from ska_tmc_centralnode.model.input import InputParameterLow

__all__ = ["LowTmcCentralNode", "main"]

# pylint:disable = attribute-defined-outside-init


class LowTmcCentralNode(AbstractCentralNode):
    """
    Central Node is a coordinator of the complete Telescope system
    """

    # -----------------
    # Device Properties
    # -----------------
    MCCSMasterLeafNodeFQDN = device_property(dtype="str")

    MCCSMasterFQDN = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    # def communication_state_callback(self):
    #     """communication state callabacks"""

    # def component_state_callback(self):
    #     """component state callbacks"""

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

            :return: A tuple containing a return code and a string message
                indicating status.The message is for information purpose only.

            :rtype: (ReturnCode, str)
            """
            super().do()

            return (ResultCode.OK, "")

    # ------------------
    # Attributes methods
    # ------------------

    @attribute(
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Schema version used for AssignResources.",
    )
    def assignResourcesSchemaVersion(self) -> str:
        """Get the version of the AssignResources schema being used."""
        return self.component_manager.assign_resources_schema_version

    @assignResourcesSchemaVersion.write
    def assignResourcesSchemaVersion_write(self, version: str) -> None:
        """Set or update the AssignResources schema version."""
        self.component_manager.assign_resources_schema_version = version
        self.push_change_archive_events(
            "assignResourcesSchemaVersion", version
        )
        self.logger.debug(
            "assignResourcesSchemaVersion updated via callback to: %s",
            version,
        )

    @attribute(
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Schema version used for ReleaseResources.",
    )
    def releaseResourcesSchemaVersion(self) -> str:
        """Get the version of the ReleaseResources schema being used."""
        return self.component_manager.release_resources_schema_version

    @releaseResourcesSchemaVersion.write
    def releaseResourcesSchemaVersion_write(self, version: str) -> None:
        """Set or update the ReleaseResources schema version."""
        self.component_manager.release_resources_schema_version = version
        self.push_change_archive_events(
            "releaseResourcesSchemaVersion", version
        )
        self.logger.debug(
            "releaseResourcesSchemaVersion updated via callback to: %s",
            version,
        )

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManagerLow(
            self.op_state_model,
            logger=self.logger,
            _update_device_callback=self.update_device_callback,
            _update_telescope_state_callback=(
                self.update_telescope_state_callback
            ),
            _update_telescope_health_state_callback=(
                self.update_telescope_health_state_callback
            ),
            _update_tmc_op_state_callback=self.update_tmc_op_state_callback,
            _update_imaging_callback=None,
            _telescope_availability_callback=(
                self.update_telescope_availability_callback
            ),
            proxy_timeout=self.ProxyTimeout,
            _input_parameter=InputParameterLow(None),
            event_subscription_check_period=self.EventSubscriptionCheckPeriod,
            liveliness_check_period=self.LivelinessCheckPeriod,
            skuid_service=self.SkuidService,
            subarray_trl_prefix=self.SubarrayPrefix,
        )
        cm.input_parameter.subarray_dev_names = self.TMCSubarrayNodes
        cm.input_parameter.mccs_mln_dev_name = (
            self.MCCSMasterLeafNodeFQDN or ""
        )
        cm.input_parameter.mccs_master_dev_name = self.MCCSMasterFQDN or ""
        cm.input_parameter.sdp_master_dev_name = self.SdpMasterFQDN or ""
        cm.input_parameter.sdp_mln_dev_name = self.SdpMasterLeafNodeFQDN or ""
        cm.input_parameter.csp_master_dev_name = self.CspMasterFQDN or ""
        cm.input_parameter.csp_mln_dev_name = self.CspMasterLeafNodeFQDN or ""
        cm.input_parameter.csp_subarray_dev_names = self.CspSubarrayLeafNodes
        cm.input_parameter.sdp_subarray_dev_names = self.SdpSubarrayLeafNodes
        cm.update_input_parameter()
        cm.setup_event_subscription()
        return cm


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
    return run((LowTmcCentralNode,), args=args, **kwargs)


if __name__ == "__main__":
    main()

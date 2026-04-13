"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""

from ska_tango_base.software_bus import Signal, attribute_from_signal
from ska_tmc_common.op_state_model import TMCOpStateModel
from tango import AttrWriteType
from tango.server import device_property, run

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

    InitCommand = None

    # -----------------
    # Device Properties
    # -----------------
    MCCSMasterLeafNodeFQDN = device_property(dtype="str", default_value="")

    MCCSMasterFQDN = device_property(dtype="str", default_value="")

    IsAutoRecoveryEnabled = device_property(
        dtype=bool,
        default_value=False,
    )

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

    # ------------------
    # Attributes methods
    # ------------------

    _assign_resources_schema_version: Signal = Signal[str](stored=True)

    def read_assignResourcesSchemaVersion(self) -> str:
        """Get the version of the AssignResources schema being used."""
        return self.component_manager.assign_resources_schema_version

    def write_assignResourcesSchemaVersion(self, version: str) -> None:
        """Set or update the AssignResources schema version."""
        self.component_manager.assign_resources_schema_version = version
        self._assign_resources_schema_version = version
        self.logger.debug(
            "assignResourcesSchemaVersion updated via callback to: %s",
            version,
        )

    assignResourcesSchemaVersion = attribute_from_signal(
        _assign_resources_schema_version,
        fget=read_assignResourcesSchemaVersion,
        fset=write_assignResourcesSchemaVersion,
        dtype=str,
        description="Schema version used for AssignResources.",
        access=AttrWriteType.READ_WRITE,
    )

    _release_resources_schema_version: Signal = Signal[str](stored=True)

    def read_releaseResourcesSchemaVersion(self) -> str:
        """Get the version of the ReleaseResources schema being used."""
        return self.component_manager.release_resources_schema_version

    def write_releaseResourcesSchemaVersion(self, version: str) -> None:
        """Set or update the ReleaseResources schema version."""
        self.component_manager.release_resources_schema_version = version
        self._release_resources_schema_version = version
        self.logger.debug(
            "releaseResourcesSchemaVersion updated via callback to: %s",
            version,
        )

    releaseResourcesSchemaVersion = attribute_from_signal(
        _release_resources_schema_version,
        fget=read_releaseResourcesSchemaVersion,
        fset=write_releaseResourcesSchemaVersion,
        dtype=str,
        description="Schema version used for ReleaseResources.",
        access=AttrWriteType.READ_WRITE,
    )

    def create_component_manager(self):
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )

        default_array_layout_url_dict = {
            "source_uris": [self.DefaultArrayLayoutSourceURIs],
            "array_layout_path": self.DefaultArrayLayoutPath,
        }

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
            array_layout_url_callback=self.update_array_layout_url_callback,
            default_array_layout_url_callback=(
                self.update_default_array_layout_url_callback
            ),
            command_timeout=self.CommandTimeOutDefault,
            proxy_timeout=self.ProxyTimeout,
            _input_parameter=InputParameterLow(None),
            event_subscription_check_period=self.EventSubscriptionCheckPeriod,
            liveliness_check_period=self.LivelinessCheckPeriod,
            subarray_trl_prefix=self.SubarrayPrefix,
            is_auto_recovery_enabled=self.IsAutoRecoveryEnabled,
            default_array_layout_url=default_array_layout_url_dict,
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

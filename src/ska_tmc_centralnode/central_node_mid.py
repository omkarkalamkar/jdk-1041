"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""

# pylint:disable = attribute-defined-outside-init
import json
import os
from threading import Event

from ska_tango_base.base import TaskCallbackType
from ska_tango_base.long_running_commands import (
    LRCReqType,
    long_running_command,
)
from ska_tango_base.software_bus import Signal, attribute_from_signal
from ska_tango_base.type_hints import TaskFunctionType
from ska_tmc_common.op_state_model import TMCOpStateModel
from tango import AttrWriteType, DebugIt
from tango.server import attribute, device_property, run

from ska_tmc_centralnode.central_node import AbstractCentralNode
from ska_tmc_centralnode.manager.component_manager_config import (
    ArrayLayoutConfig,
    DishVccConfig,
    GPMConfig,
    MidCentralNodeComponentManagerConfig,
    TimeoutConfig,
)
from ska_tmc_centralnode.manager.component_manager_mid import (
    CNComponentManagerMid,
)
from ska_tmc_centralnode.model.component import CentralComponent
from ska_tmc_centralnode.model.enum import DishConfigStatus, ModesAvailability
from ska_tmc_centralnode.model.input import InputParameterMid
from ska_tmc_centralnode.utils.json_validator_decorator import (
    validate_dish_vcc_command_status,
)

__all__ = ["MidTmcCentralNode", "main"]

# pylint:disable=invalid-name #Due to tango camel case


class MidTmcCentralNode(AbstractCentralNode):
    """
    Central Node is a coordinator of the complete Telescope system

    """

    InitCommand = None

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

    DishMasterFQDNs = device_property(
        dtype=("str",),
        doc="List of Dish Master devices",
        default_value=tuple(),
    )

    DishMasterIdentifier = device_property(
        dtype="str",
        doc="Device name tag for Dish Master device",
        default_value="",
    )

    DishVccUri = device_property(
        dtype="str",
        doc="Default DishVccConfig URI",
        default_value="",
    )

    DishVccFilePath = device_property(
        dtype="str",
        doc="Default DishVccConfig File Path",
        default_value="",
    )

    EnableDishVccInit = device_property(
        dtype=bool,
        doc="If true then only load dish vcc during initialization",
        default_value=True,
    )

    DishVccInitTimeout = device_property(dtype="DevUShort", default_value=120)

    DishKvalueAggregationAllowedPercent = device_property(
        dtype="DevDouble", default_value=100.0
    )

    KValueValidRangeUpperLimit = device_property(
        dtype=int,
        default_value=1177,
        doc="the valid k-value range",
    )

    KValueValidRangelowerLimit = device_property(
        dtype=int,
        default_value=1,
        doc="the valid k-value range",
    )

    GPMVersion = device_property(dtype="str", default_value="")

    GPMInterface = device_property(
        dtype="str",
        doc="Default GPM interface",
        default_value="",
    )

    GPMDataSourcesPrefix = device_property(
        dtype="str",
        doc="Default GPM data source prefix",
        default_value="",
    )

    GPMFilePathPrefix = device_property(
        dtype="str",
        doc="Default GPM data file path prefix",
        default_value="",
    )

    MeerKatExtensionID = device_property(
        dtype=str, doc="ID of Meerkat Extension dishes.", default_value=""
    )

    MeerKatDishIdLowerLimit = device_property(
        dtype=int, doc="Lower limit of Meerkat Dish IDs.", default_value=0
    )
    MeerKatDishIdUpperLimit = device_property(
        dtype=int, doc="Upper limit of Meerkat Dish IDs.", default_value=63
    )
    SkaDishIdLowerLimit = device_property(
        dtype=int, doc="Lower limit of SKA Dish IDs.", default_value=1
    )
    SkaDishIdUpperLimit = device_property(
        dtype=int, doc="Upper limit of SKA Dish IDs.", default_value=999
    )

    # ----------
    # Attributes
    # ----------

    imaging = attribute_from_signal(
        "_component_manager.component._imaging",
        dtype=ModesAvailability,
        description="Imaging Attribute",
        access=AttrWriteType.READ,
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

    _is_dish_vcc_config_set: Signal[bool] = Signal[bool](
        stored=True, initial_value=True
    )

    isDishVccConfigSet = attribute_from_signal(
        "_component_manager._is_dish_vcc_config_set",
        dtype=bool,
        access=AttrWriteType.READ,
    )

    DishVccCommandStatus = attribute_from_signal(
        "_component_manager._dish_vcc_command_status",
        dtype=DishConfigStatus,
        access=AttrWriteType.READ,
    )

    DishVccValidationStatus = attribute_from_signal(
        "_component_manager._dish_vcc_validation_status",
        dtype=str,
        access=AttrWriteType.READ,
    )

    GlobalPointingModelStatus = attribute_from_signal(
        "_component_manager._global_pointing_model_status",
        dtype=str,
        access=AttrWriteType.READ,
        to_tango=json.dumps,
    )

    # ---------------
    # General methods
    # ---------------

    # ------------------
    # Attributes methods
    # ------------------

    def read_pss(self):
        """Read attribute for pss"""
        return self.component_manager.component.pss

    def read_pst(self):
        """Read attribute value of pst"""
        return self.component_manager.component.pst

    def read_vlbi(self):
        """Read attribute value of vlbi"""
        return self.component_manager.component.vlbi

    def _get_component_manager_config(
        self,
    ) -> MidCentralNodeComponentManagerConfig:
        """Provides the configuration for component manager Mid.

        :return: Instance of MidCentralNodeComponentManagerConfig.
        :rtype: MidCentralNodeComponentManagerConfig
        """
        _component = CentralComponent(logger=self.logger)

        _component.shared_bus = self.shared_bus
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        default_array_layout_url_dict = {
            "source_uris": [self.DefaultArrayLayoutSourceURIs],
            "array_layout_path": self.DefaultArrayLayoutPath,
        }
        return MidCentralNodeComponentManagerConfig(
            component=_component,
            op_state_model=self.op_state_model,
            input_parameter=InputParameterMid(None),
            logger=self.logger,
            dish_config=DishVccConfig(
                uri=self.DishVccUri if self.DishVccUri else "",
                file_path=self.DishVccFilePath if self.DishVccFilePath else "",
                init_timeout=self.DishVccInitTimeout,
                dish_k_value_aggregation_allowed_precent=(
                    self.DishKvalueAggregationAllowedPercent
                ),
                k_value_valid_range_lower_limit=(
                    self.KValueValidRangelowerLimit
                ),
                k_value_valid_range_upper_limit=(
                    self.KValueValidRangeUpperLimit
                ),
                invoke_command_callback=(
                    self.invoke_load_dish_cfg_command_callback
                ),
                enable_init=self.EnableDishVccInit,
            ),
            gpm_config=GPMConfig(
                version=self.GPMVersion,
                interface=self.GPMInterface,
                data_sources_prefix=self.GPMDataSourcesPrefix,
                file_path_prefix=self.GPMFilePathPrefix,
                invoke_command_callback=self.invoke_set_gpm_command_callback,
            ),
            timeout_config=TimeoutConfig(
                command_timeout=self.CommandTimeOutDefault,
                proxy_timeout=self.ProxyTimeout,
                event_subscription_check_period=(
                    self.EventSubscriptionCheckPeriod
                ),
                liveliness_check_period=self.LivelinessCheckPeriod,
            ),
            array_layout_config=ArrayLayoutConfig(
                default_url=default_array_layout_url_dict,
            ),
            subarray_trl_prefix=self.SubarrayPrefix,
            mkt_extension_id=self.MeerKatExtensionID,
            ska_dish_ranges=(
                self.SkaDishIdLowerLimit,
                self.SkaDishIdUpperLimit,
            ),
            mkt_dish_ranges=(
                self.MeerKatDishIdLowerLimit,
                self.MeerKatDishIdUpperLimit,
            ),
        )

    def _update_fqdns(self, cm: CNComponentManagerMid) -> None:
        """Updates the FQDN's in input parameter.

        :param cm: Instance of CNComponentManagerMid.
        :type cm: CNComponentManagerMid
        """
        cm.input_parameter.dish_leaf_node_dev_names = []
        cm.input_parameter.dish_dev_names = []
        for dish in self.DishIDs:
            dishln_name: str = os.path.join(self.DishLeafNodePrefix, dish)
            cm.input_parameter.dish_leaf_node_dev_names.append(
                dishln_name.lower()
            )

        for dish_name in self.DishMasterFQDNs:
            cm.input_parameter.dish_dev_names.append(dish_name)
        cm.input_parameter.subarray_dev_names = self.TMCSubarrayNodes
        cm.input_parameter.csp_master_dev_name = self.CspMasterFQDN or ""
        cm.input_parameter.csp_mln_dev_name = self.CspMasterLeafNodeFQDN or ""
        cm.input_parameter.sdp_master_dev_name = self.SdpMasterFQDN or ""
        cm.input_parameter.sdp_mln_dev_name = self.SdpMasterLeafNodeFQDN or ""
        cm.input_parameter.csp_subarray_dev_names = self.CspSubarrayLeafNodes
        cm.input_parameter.sdp_subarray_dev_names = self.SdpSubarrayLeafNodes
        cm.input_parameter.dish_leaf_node_prefix = self.DishLeafNodePrefix
        cm.input_parameter.dish_master_identifier = self.DishMasterIdentifier

    def create_component_manager(self):
        """
        Creates and configures the Component Manager for this device.
        :return: The configured Component Manager instance.
        :rtype: CNComponentManagerMid
        """
        self.op_state_model = TMCOpStateModel(
            logger=self.logger, callback=super()._update_state
        )
        cm = CNComponentManagerMid(self._get_component_manager_config())
        self._update_fqdns(cm)
        cm.update_input_parameter()
        cm.setup_event_subscription()
        return cm

    def invoke_load_dish_cfg_command_callback(self):
        """This callback is called when dishVccValidationResult is Unknown
        and Central Node needs to load dish cfg on csp
        """
        dish_cfg_json = json.dumps(
            self.component_manager.get_default_dish_vcc_config_params()
        )
        self.LoadDishCfg(dish_cfg_json)

    def invoke_set_gpm_command_callback(self):
        """This callback is called when dishVccValidationResult is Unknown
        and Central Node needs to load dish cfg on csp
        """

        self.SetGlobalPointingModel(
            json.dumps(self.component_manager.get_default_gpm_version_params())
        )

    # pylint: disable=unused-argument
    def is_LoadDishCfg_allowed(
        self, request_type: LRCReqType | None = None
    ) -> bool:
        """
        Checks whether LoadDishCfg command is allowed to be run
        in current device state.

        :rtype: boolean
        """
        return True

    # pylint: enable=unused-argument

    @validate_dish_vcc_command_status
    @long_running_command
    @DebugIt()
    def LoadDishCfg(self, argin: str) -> TaskFunctionType:
        """
        LoadDishCfg command to load dishID-vcc map config.
        This command get dishid-vcc map json string from Telmodel
        based on tm data sources provided in argin.

        .. code-block::
            :caption: Example

            {
                "interface":
                "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2",
                "tm_data_sources":["car://gitlab.com/ska-telescope/
                ska-tmc/ska-tmc-simulators?main#tmdata"],
                "tm_data_filepath": "instrument/dishid_vcc_map_configuration/
                mid_cbf_initial_parameters.json"
            }

        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.load_dish_cfg(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    # pylint: disable=unused-argument
    def is_SetGlobalPointingModel_allowed(
        self, request_type: LRCReqType | None = None
    ) -> bool:
        """
        Checks whether setGlobalPointingModel command is allowed to be run
        in current device state.

        :rtype: boolean
        """
        return True

    # pylint: enable=unused-argument

    @long_running_command
    @DebugIt()
    def SetGlobalPointingModel(self, argin: str) -> TaskFunctionType:
        """
        SetGlobalPointingModel command to send the GPM URI to dish leaf
        nodes. This command gets a dictionary in following form:

        .. code-block::
            :caption: Example

            {
                # Versioned tag of git where all the GPM files are available
                # for applying to the respective dishes for their respective
                # bands.
                "version": "1.0",
                "receptors":
                    {
                        "SKA001":['Band_1','Band_2'],
                        "SKA002":['Band_2']
                    }
            }
            Data formed for Dish Leaf node ApplyPointingModel command:
            {
                "interface": "https://schema.skao.int/ska-mid-global
                -pointing-model/1.0",
                "tm_data_sources":
                ["car://gitlab.com/ska-telescope/ska-tmc/ska-tmc-simu
                lators?1.0#tmdata"],
                "tm_data_filepath":
                "instrument/ska_mid1/global_pointing_model_data/gpm-
                ska001-Band_1.json"
            }
        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.set_gpm_version(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    # pylint: disable=unused-argument
    def is_SetStowMode_allowed(
        self, request_type: LRCReqType | None = None
    ) -> bool:
        """
        Checks whether setStowMode command is allowed to be run
        in current device state.

        :rtype: boolean
        """
        return True

    # pylint: enable=unused-argument

    @long_running_command
    @DebugIt()
    def SetStowMode(self, argin: str) -> TaskFunctionType:
        """
        SetStowMode command to send the stow mode command to dish leaf
        nodes. This command gets a list in following form:

        .. code-block::
            :caption: Example

            To Specific Dishes = ["SKA001","SKA002", ...]
            To all Dishes = ["ALL"]
        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.set_stow_mode(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task


# pylint:enable=invalid-name

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
    return run((MidTmcCentralNode,), args=args, **kwargs)


if __name__ == "__main__":
    main()

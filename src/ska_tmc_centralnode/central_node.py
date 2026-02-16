"""
Central Node is a coordinator of the complete M&C system.
Central Node implements the standard set
of state and mode attributes defined by the SKA Control Model.
"""

# pylint:disable = attribute-defined-outside-init
import json
from threading import Event
from typing import List, Tuple, Union

import tango
from ska_control_model import HealthState, ResultCode
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.long_running_commands import (
    LRCReqType,
    long_running_command,
)
from ska_tango_base.software_bus import Signal, attribute_from_signal
from ska_tmc_common.exceptions import CommandNotAllowed, DeviceUnresponsive
from ska_tmc_common.v1.tmc_base_device import TMCBaseDevice
from tango import ApiUtil, AttrWriteType, Database, DebugIt
from tango.server import attribute, command, device_property

from ska_tmc_centralnode import release
from ska_tmc_centralnode.utils.json_validator_decorator import (
    assign_validate_json_args,
    release_validate_json_args,
)


class AbstractCentralNode(TMCBaseDevice):
    """
    Central Node is a coordinator of the complete Telescope system.
    Central Node is inherited from TMCBaseDevice class which is further
    inherited from SKABaseDevice class. TMCBaseDevice class contains
    attributes common to CentralNode and SubarrayNode.
    """

    InitCommand = None

    # -----------------
    # Device Properties
    # -----------------
    def _memorize_attr(self, attr_name: str, json_string_value: str) -> None:
        """
        Persist an attribute value into Tango DB in the right format.
        attr_name must match the Tango attribute name exactly.
        json_string_value must be a JSON-encoded string (ex:json.dumps(dict)).
        """
        try:
            db = Database()
            props = {attr_name: {"__value": [json_string_value]}}
            # Use the server's own FQDN
            device_fqdn = self.get_name()
            db.put_device_attribute_property(device_fqdn, props)
            self.logger.debug(
                "Memorized %s in DB with value: %s",
                attr_name,
                json_string_value,
            )
        except Exception:
            # Don't crash your server if DB is unavailable
            self.logger.exception("Failed to memorize %s in DB", attr_name)

    def update_array_layout_url_callback(self, url_dict: dict) -> None:
        """
        Called by the component manager whenever the array_layout_url changes.
        Persists the value in the Tango DB and pushes change/archive events.

        Args:
            url_dict (dict): Dictionary containing the array layout URL
            information to be serialized and stored.
        """
        json_value = json.dumps(url_dict)
        self._memorize_attr("arrayLayoutURL", json_value)
        self._array_layout_url = json_value

    def update_default_array_layout_url_callback(self, url_dict: dict) -> None:
        """
        Called by the component manager whenever the default_array_layout_url
        changes. Persists the value in the Tango DB and pushes change/archive
        events.

        Args:
            url_dict (dict): Dictionary containing the default array layout URL
                information to be serialized and stored.
        """
        json_value = json.dumps(url_dict)
        self._memorize_attr("DefaultArrayLayoutURL", json_value)
        self._default_array_layout_url = json_value

    TMCSubarrayNodes = device_property(
        dtype=("str",),
        doc="List of TMC Mid Subarray Node devices",
        default_value=tuple(),
    )
    CspMasterLeafNodeFQDN = device_property(dtype="str")

    CspMasterFQDN = device_property(dtype="str")

    SdpMasterLeafNodeFQDN = device_property(dtype="str")

    SdpMasterFQDN = device_property(dtype="str")

    CspSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of CspSubarrayLeafNode devices",
        default_value=tuple(),
    )

    SdpSubarrayLeafNodes = device_property(
        dtype=("str",),
        doc="List of SdpSubarrayLeafNode devices",
        default_value=tuple(),
    )

    ProxyTimeout = device_property(dtype="DevUShort", default_value=500)

    SubarrayPrefix = device_property(
        dtype="DevString",
        default_value="",
    )

    DefaultArrayLayoutSourceURIs = device_property(
        dtype="DevString",
        doc=(
            "Default source URIs for the Array Layout. "
            "Defines the TelModel repository source(s). Example: "
            '["gitlab://gitlab.com/ska-telescope/'
            'ska-telmodel-data?main#tmdata"]'
        ),
    )

    DefaultArrayLayoutPath = device_property(
        dtype="str",
        doc=(
            "Default array layout path within the TelModel data. "
            "Example: 'instrument/ska1_mid/layout/mid-layout.json'"
        ),
    )
    # ----------------------
    # Attributes and methods
    # ----------------------

    telescopeHealthState = attribute(
        dtype=HealthState,
        doc="Health state of Telescope",
    )

    # _telescope_state: Signal[tango.DevState] = Signal[tango.DevState](
    #     stored=True, initial_value=tango.DevState.UNKNOWN
    # )

    def read_telescopeState(self):
        """Reads telescopeState"""
        return self.component_manager.component.telescope_state

    telescopeState = attribute(
        dtype=tango.DevState,
        doc="DevState of telescope",
    )

    # telescopeState = attribute_from_signal(
    #     _telescope_state,
    #     dtype="DevState",
    #     description="DevState of telescope",
    #     access=AttrWriteType.READ,
    # )

    _desired_telescope_state: Signal[tango.DevState] = Signal[tango.DevState](
        stored=True, initial_value=tango.DevState.ON
    )

    def read_desiredTelescopeState(self):
        """Read Desired TelescopeState"""
        return self.component_manager.component.desired_telescope_state

    desiredTelescopeState = attribute_from_signal(
        _desired_telescope_state,
        fget=read_desiredTelescopeState,
        dtype="DevState",
        description="desiredTelescopeState attribute of Central Node.",
        access=AttrWriteType.READ,
    )

    _array_layout_url: Signal = Signal[str](stored=True)

    def read_arrayLayoutURL(self) -> str:
        """Returns the array layout URL attribute value."""
        return json.dumps(self.component_manager.array_layout_url)

    def write_arrayLayoutURL(self, url: str) -> None:
        """Set the Array Layout URL value.

        Args:
            uri (str): Array Layout URL
        """
        self.component_manager.array_layout_url = json.loads(url)

    arrayLayoutURL = attribute_from_signal(
        _array_layout_url,
        fget=read_arrayLayoutURL,
        fset=write_arrayLayoutURL,
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
    )

    _default_array_layout_url: Signal = Signal[str](stored=True)

    def read_DefaultArrayLayoutURL(self) -> str:
        """Returns the default array layout URL attribute value."""
        return json.dumps(self.component_manager.default_array_layout_url)

    def write_DefaultArrayLayoutURL(self, url: str) -> None:
        """Sets the default array layout URL."""
        self.component_manager.default_array_layout_url = json.loads(url)

    DefaultArrayLayoutURL = attribute_from_signal(
        _default_array_layout_url,
        fget=read_DefaultArrayLayoutURL,
        fset=write_DefaultArrayLayoutURL,
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
    )

    _tm_op_state: Signal[tango.DevState] = Signal[str](
        stored=True, initial_value=tango.DevState.UNKNOWN
    )

    def read_tmOpState(self):
        """Return the tmOpState attribute."""
        return self.component_manager.component.tmc_op_state

    tmOpState = attribute_from_signal(
        _tm_op_state,
        fget=read_tmOpState,
        dtype="DevState",
        access=AttrWriteType.READ,
    )

    _telescope_availability: Signal[str] = Signal[str](
        stored=True, initial_value=""
    )

    def read_telescopeAvailability(self):
        "Returns telescope availability"
        return json.dumps(
            self.component_manager.component.telescope_availability
        )

    telescopeAvailability = attribute_from_signal(
        _telescope_availability,
        fget=read_telescopeAvailability,
        dtype=str,
        access=AttrWriteType.READ,
    )

    def update_device_callback(self, devInfo):
        """Update device callabacks"""
        self.last_device_info_changed = devInfo.to_json()
        self.push_change_archive_events(
            "lastDeviceInfoChanged", devInfo.to_json()
        )

    def update_telescope_state_callback(self, telescope_state):
        """Update telescope state callback"""
        self.logger.info("Updating telescope state %s", telescope_state)
        # self._telescope_state = telescope_state
        self.push_change_archive_events("telescopeState", telescope_state)

    def update_telescope_health_state_callback(self, telescope_health_state):
        """Update Telescope health state callbacks"""
        self.logger.debug(
            "Pushing telescopeHealthState event %s", telescope_health_state
        )
        self.push_change_archive_events(
            "telescopeHealthState", telescope_health_state
        )

    def update_tmc_op_state_callback(self, tmc_op_state):
        """Update tmc operational state callbacks"""
        self._tm_op_state = tmc_op_state

    def update_telescope_availability_callback(self, telescope_availability):
        """Update device availabililty callbacks"""
        self._telescope_availability = json.dumps(telescope_availability)

    # ---------------
    # General methods
    # ---------------

    def init_device(self) -> None:
        """
        Initializes the CentralNode device.
        """
        super().init_device()
        self._build_state = (
            f"{release.name},{release.version},{release.description}"
        )

        self._version_id = release.version
        self.last_device_info_changed = ""
        for attribute_name in [
            "lastDeviceInfoChanged",
            "telescopeState",
            "telescopeHealthState",
        ]:
            self.set_change_event(attribute_name, True, False)
            self.set_archive_event(attribute_name, True)

        ApiUtil.instance().set_asynch_cb_sub_model(
            tango.cb_sub_model.PUSH_CALLBACK
        )
        self._health_state = HealthState.OK
        self.op_state_model.perform_action("component_on")

        self.init_completed()

    # ------------------
    # Attributes methods
    # ------------------

    def read_telescopeHealthState(self):
        """Read value of telescopeHealthState"""
        return self.component_manager.component.telescope_health_state

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

    # --------
    # Commands
    # --------

    def is_TelescopeOn_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether this command is allowed to be run in current device
            state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed("TelescopeOn")
        return self.component_manager.is_command_allowed_before_lrc_start(
            command_name="TelescopeOn"
        )

    @long_running_command
    @DebugIt()
    def TelescopeOn(self) -> Tuple[List[ResultCode], List[str]]:
        """
        This command invokes TelescopeOn() command on DishLeadNode,
        CspMasterLeafNode,SdpMasterLeafNode.
        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.telescope_on(
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def is_TelescopeStandby_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether this command is allowed to be run in current device
        state.

        :return: True if this command is allowed to be run in current device
            state.

        :rtype: boolean
        """
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed(
                "TelescopeStandby"
            )
        return self.component_manager.is_command_allowed_before_lrc_start(
            command_name="TelescopeStandby"
        )

    @long_running_command
    @DebugIt()
    def TelescopeStandby(self) -> Tuple[List[ResultCode], List[str]]:
        """
        This command invokes TelescopeStandby() command on CspMasterLeafNode,
        SdpMasterLeafNode and DishLeafNode.

        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.telescope_standby(
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def is_TelescopeOff_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether this command is allowed to be run in current
        device state.

        :return: True if this command is allowed to be run in current
            device state.

        :rtype: boolean
        """
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed("TelescopeOff")
        return self.component_manager.is_command_allowed_before_lrc_start(
            command_name="TelescopeOff"
        )

    @long_running_command
    @DebugIt()
    def TelescopeOff(self) -> Tuple[List[ResultCode], List[str]]:
        """
        This command invokes SetStandbyLPMode() command on DishLeafNode, Off()
        command on CspMasterLeafNode and SdpMasterLeafNode.

        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.telescope_off(
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

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
    @DebugIt()
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

    def is_AssignResources_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether AssignResources command is allowed with the given input.

        :param argin: The command input argument
        :param request_type: The type of request (ENQUEUE_REQ or EXECUTE_REQ)
        :return: True if AssignResources is allowed
            to be run in current device state

        :rtype: boolean
        """
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed("AssignResources")

        return True

    # pylint: disable=unnecessary-pass
    def completed_AssignResources(self) -> None:
        """AssignResources command completed callback."""
        pass

    # pylint: enable=unnecessary-pass
    @assign_validate_json_args
    @long_running_command
    @DebugIt()
    def AssignResources(
        self, argin: str
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        AssignResources command invokes the AssignResources command on
            lower level devices.
        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.assign_resources(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def is_ReleaseResources_allowed(
        self, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ
    ) -> Union[bool, CommandNotAllowed, DeviceUnresponsive]:
        """
        Checks whether ReleaseResources is allowed with the given input.

        :param argin: The command input argument
        :param request_type: The type of request (ENQUEUE_REQ or EXECUTE_REQ)
        :return: True if ReleaseResources command is allowed to be run in
            current device state.

        :rtype: boolean
        """
        if request_type == LRCReqType.ENQUEUE_REQ:
            return self.component_manager.is_command_allowed(
                "ReleaseResources"
            )

        return True

    @release_validate_json_args
    @long_running_command
    @DebugIt()
    def ReleaseResources(
        self, argin: str
    ) -> Tuple[List[ResultCode], List[str]]:
        """
        Releases all the resources assigned to the given Subarray.
        """

        def task(
            task_callback: TaskCallbackType, task_abort_event: Event
        ) -> None:
            self.component_manager.release_resources(
                argin=argin,
                task_callback=task_callback,
                task_abort_event=task_abort_event,
            )

        return task

    def create_component_manager(self):
        """Create component manager object for command invocation."""

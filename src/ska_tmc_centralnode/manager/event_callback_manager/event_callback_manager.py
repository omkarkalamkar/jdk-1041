"""Module to manage all the event callbacks.
"""
from __future__ import annotations

import threading
import time
from logging import Logger
from typing import Callable, Union

from ska_control_model import AdminMode, HealthState, ObsState

from ska_tmc_centralnode.utils.constants import (
    LOW_CSP_MLN_DEVICE,
    LOW_SDP_MLN_DEVICE,
    MCCS_MLN_DEVICE,
    MID_CSP_MLN_DEVICE,
    MID_SDP_MLN_DEVICE,
)

from ...model.component import TmcComponent
from ...model.input import InputParameterLow, InputParameterMid
from ..event_data_manager import EventDataManager


class EventCallbackManager:
    """Class to manage change event callbacks for both Mid and
    Low telescope."""

    def __init__(
        self,
        logger: Logger,
        component: TmcComponent,
        command_completion_cond: threading.Condition,
        input_parameter: Union[InputParameterMid, InputParameterLow],
        event_data_manager: EventDataManager,
        _aggregate_state: Callable,
    ):
        self.logger = logger
        self.component = component
        self.command_completion_cond = command_completion_cond
        self.input_parameter = input_parameter
        self.event_data_manager = event_data_manager
        self.rlock = threading._RLock()
        self.lock = threading.Lock()
        self._aggregate_state = _aggregate_state
        self.dish_vcc_validation_attr_lock = threading.Lock()

    def update_device_obs_state(
        self, dev_name: str, obs_state: ObsState
    ) -> None:
        """
        Update a monitored device obs state,
        and call the relative callbacks if available

        :param dev_name: name of the device
        :type dev_name: str
        :param obs_state: obs state of the device
        :type obs_state: ObsState
        """
        with self.rlock:
            self.logger.debug(
                f"obsState event for {dev_name}: {ObsState(obs_state).name}"
            )
            sdp_subarray_dev_names = (
                self.input_parameter.sdp_subarray_dev_names
            )
            for sdp_subarray in sdp_subarray_dev_names:
                if dev_name in sdp_subarray:
                    dev_name = sdp_subarray

            # TODO: Enable this fix when real CSP controller and CSP Subarray
            # exposes full FQDN, in integration
            # csp_subarray_dev_names = self.get_csp_subarray_dev_names()
            # for csp_subarray in csp_subarray_dev_names:
            #     if dev_name in csp_subarray:
            #         dev_name = csp_subarray

            dev_info = self.component.get_device(dev_name)
            if dev_info is not None:
                dev_info.obs_state = obs_state
                self.logger.debug(
                    "Updated ObsState of %s: %s",
                    dev_info.dev_name,
                    ObsState(dev_info.obs_state).name,
                )
                with self.command_completion_cond:
                    self.command_completion_cond.notify_all()
                dev_info.last_event_arrived = time.time()
                self.component.last_device_info_changed = dev_info

    def _get_sdp_subarray_name(self, device_name: str):
        """Provides SDP subarray device name which is stored in device
        Information.

        :param device_name: Device FQDN received in event.
        :type device_name: str
        """
        sdp_subarray_dev_names = self.input_parameter.sdp_subarray_dev_names
        for sdp_subarray in sdp_subarray_dev_names:
            if device_name in sdp_subarray:
                device_name = sdp_subarray
        return device_name

    def update_device_assigned_resource(
        self, dev_name: str, assign_resources: str
    ) -> None:
        """
        Update assign_resources for a monitored device

        :param dev_name: name of the device
        :type dev_name: str
        :param assign_resources: assigned resources in JSON format
        :type assign_resources: str
        """
        with self.lock:
            self.logger.debug(
                "Updating assigned resources for device %s: %s",
                dev_name,
                assign_resources,
            )
            device_name = self._get_sdp_subarray_name(dev_name)
            dev_info = self.component.get_device(device_name)
            if dev_info is not None:
                dev_info.resources = assign_resources
                dev_info.last_event_arrived = time.time()
                self.component.last_device_info_changed = dev_info

    def _get_master_device_name(self, device_name: str):
        """Provides Master device name which is stored in device info.

        :param device_name: Device FQDN received in event.
        :type device_name: str
        """
        if "sdp" in device_name:
            # Update SDP Master device name with full FQDN for real SDP
            sdp_master_dev_name = self.input_parameter.sdp_master_dev_name
            if device_name in sdp_master_dev_name:
                device_name = sdp_master_dev_name
        elif "csp" in device_name:
            # Update CSP Master device name with full FQDN for real CSP
            csp_master_dev_name = self.input_parameter.csp_master_dev_name
            if device_name in csp_master_dev_name:
                device_name = csp_master_dev_name
        return device_name

    def update_device_health_state(
        self, device_name: str, health_state: HealthState, timestamp
    ) -> None:
        """
        Update a monitored device health state
        aggregate the health states available

        Args:
            dev_name (str): name of the device
            health_state (HealthState): health state of the device
            timstamp: timestamp

        """
        with self.lock:
            self.logger.debug(
                f"healthState event for {device_name}: "
                + f"{HealthState(health_state).name}"
            )
            device_name = self._get_master_device_name(device_name)
            dev_info = self.component.get_device(device_name)
            if dev_info is not None:
                dev_info.health_state = health_state
                self.logger.debug(
                    "Updated healthState of %s: %s",
                    dev_info.dev_name,
                    HealthState(dev_info.health_state).name,
                )
                dev_info.last_event_arrived = time.time()
                self.event_data_manager.update_event_data(
                    device=device_name,
                    data=health_state,
                    received_timestamp=timestamp,
                    data_type="HealthState",
                )
                self.component.last_device_info_changed = dev_info

    def update_device_admin_mode(
        self, device_name: str, admin_mode: AdminMode, timestamp
    ):
        """
        Update a monitored device admin mode

        :param device_name: name of the device
        :type device_name: str
        :param admin_mode: admin mode of the device
        :type admin_mode: AdminMode
        """
        self.logger.debug(
            f"AdminMode event for {device_name}: "
            + f"{AdminMode(admin_mode).name}"
        )
        with self.lock:
            leafnode_identifiers = [
                MID_SDP_MLN_DEVICE,
                MID_CSP_MLN_DEVICE,
                LOW_SDP_MLN_DEVICE,
                LOW_CSP_MLN_DEVICE,
                MCCS_MLN_DEVICE,
            ]
            if any(
                identifier in device_name.lower()
                for identifier in leafnode_identifiers
            ):
                device_info = self.component.get_device(device_name)
                if device_info is not None:
                    device_info.last_event_arrived = time.time()
                    device_info.admin_mode = admin_mode
                    self.event_data_manager.update_event_data(
                        device=device_name,
                        data=admin_mode,
                        data_type="AdminMode",
                        received_timestamp=timestamp,
                    )
                    self.component.last_device_info_changed = device_info

    def update_device_state(self, device_name, state):
        """
        Update a monitored device state,
        aggregate the states available
        and call the relative callbacks if available

        :param device_name: name of the device
        :type device_name: str
        :param state: state of the device
        :type state: DevState
        """
        with self.rlock:
            self.logger.debug("State event for %s: %s", device_name, state)
            device_name = self._get_master_device_name(device_name)
            dev_info = self.component.get_device(device_name)
            if dev_info is not None:
                dev_info.state = state
                self.logger.debug(
                    "Updated State of %s: %s ",
                    dev_info.dev_name,
                    dev_info.state,
                )
                dev_info.last_event_arrived = time.time()
                self.component.last_device_info_changed = dev_info
        self._aggregate_state()

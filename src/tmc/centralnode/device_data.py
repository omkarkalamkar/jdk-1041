# -*- coding: utf-8 -*-
#
# This file is part of the CentralNode project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
""" Device Data
This module defines the DeviceData class, which represents of the functional CentralNode device.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
from ska.base.control_model import HealthState
from tmc.centralnode import const
import threading

# PROTECTED REGION END #    //  CentralNode.additional_import


class DeviceData:
    """
    This class represents the CentralNode
    as functional device. It mainly comprise the data common
    across various functions of a central node.
    """

    __instance = None

    def __init__(self):
        """Private constructor of the class"""
        if DeviceData.__instance is not None:
            raise Exception("This is singleton class")
        else:
            DeviceData.__instance = self

        # Create event for attribute callback trigger
        self._state_callback_trigger = threading.Event()
        self._telstate_callback_trigger = threading.Event()
        self._tmc_off_trigger = threading.Event()

        self._sdp_master_health = HealthState.UNKNOWN
        self._csp_master_health = HealthState.UNKNOWN
        self._csp_master_state = ""
        self._sdp_master_state = ""
        self.receptorIDList = []
        self.subarray_health_state_map = {}
        self._dish_leaf_node_devices = []
        self._leaf_device_proxy = []
        self.subarray_FQDN_dict = {}
        self.sln_prefix = ""
        self.health_aggreegator = None
        self.state_aggregator = None
        self.telescope_state_aggregator = None
        self.resource_manager = None
        self.obs_state_aggregator = None
        self.check_resources = None
        self.desired_telescope_state = {}
        self.command_in_progress = ""
        self.tmc_device_states = []
        self.telescope_device_states = []

        self.subarray_obsstate_map = {}
        self.list_subarray_obsstate = []

    @staticmethod
    def get_instance():
        if DeviceData.__instance is None:
            DeviceData()
        return DeviceData.__instance

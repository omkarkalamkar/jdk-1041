"""Input Parameter class for central node"""
from typing import Callable, List


class InputParameter:
    """Class for Input parameter this class is used to distinguish between
    between low and mid telescope"""

    def __init__(self, changed_callback: Callable) -> None:
        self._changed_callback: Callable = changed_callback
        self._subarray_dev_names: List[str] = []
        self._csp_subarray_dev_names: List[str] = []
        self._sdp_subarray_dev_names: List[str] = []
        self._csp_master_dev_name: str = ""
        self._sdp_master_dev_name: str = ""
        self._sdp_mln_dev_name: str = ""
        self._csp_mln_dev_name: str = ""

    @property
    def csp_subarray_dev_names(self) -> List[str]:
        """
        Input parameter
        Return the CSP Subarray device names

        :return: the CSP Subarray device names
        :rtype: list
        """
        return self._csp_subarray_dev_names

    @csp_subarray_dev_names.setter
    def csp_subarray_dev_names(self, value: List[str]) -> None:
        """
        Input parameter
        Set the CSP Subarray device names to be
        managed by the CentralNode

        :param value: the CSP Subarray device names
        :type value: tuple
        """
        self._csp_subarray_dev_names = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def sdp_subarray_dev_names(self) -> List[str]:
        """
        Input parameter
        Return the SDP Subarray device names

        :return: the SDP Subarray device names
        :rtype: tuple
        """
        return self._sdp_subarray_dev_names

    @sdp_subarray_dev_names.setter
    def sdp_subarray_dev_names(self, value: List[str]):
        """
        Input parameter
        Set the SDP Subarray device names to be
        managed by the CentralNode

        :param value: the SDP Subarray device names
        :type value: tuple
        """
        self._sdp_subarray_dev_names = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def csp_master_dev_name(self) -> str:
        """
        Input parameter
        Return the CSP Master device name

        :return: the CSP Master device name
        :rtype: str
        """
        return self._csp_master_dev_name

    @csp_master_dev_name.setter
    def csp_master_dev_name(self, value: str) -> None:
        """
        Input parameter
        Set the CSP Master device name to be
        managed by the CentralNode

        :param value: the CSP Master device name
        :type value: str
        """
        self._csp_master_dev_name = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def sdp_master_dev_name(self) -> str:
        """
        Input parameter
        Return the SDP Master device name

        :return: the SDP Master device name
        :rtype: str
        """
        return self._sdp_master_dev_name

    @sdp_master_dev_name.setter
    def sdp_master_dev_name(self, value: str) -> None:
        """
        Input parameter
        Set the SDP Master device name to be
        managed by the CentralNode

        :param value: the SDP Master device name
        :type value: str
        """
        self._sdp_master_dev_name = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def csp_mln_dev_name(self) -> str:
        """
        Input parameter
        Return the CSP Master device name

        :return: the CSP Master device name
        :rtype: str
        """
        return self._csp_mln_dev_name

    @csp_mln_dev_name.setter
    def csp_mln_dev_name(self, value: str) -> None:
        """
        Input parameter
        Set the CSP Master device name to be
        managed by the CentralNode

        :param value: the CSP Master device name
        :type value: str
        """
        self._csp_mln_dev_name = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def sdp_mln_dev_name(self) -> str:
        """
        Input parameter
        Return the SDP Master device name

        :return: the SDP Master device name
        :rtype: str
        """
        return self._sdp_mln_dev_name

    @sdp_mln_dev_name.setter
    def sdp_mln_dev_name(self, value: str) -> None:
        """
        Input parameter
        Set the SDP Master device name to be
        managed by the CentralNode

        :param value: the SDP Master device name
        :type value: str
        """
        self._sdp_mln_dev_name = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def subarray_dev_names(self) -> List[str]:
        """
        Input parameter
        Return the SubarrayNode device names

        :return: the SubarrayNode device names
        :rtype: tuple
        """
        return self._subarray_dev_names

    @subarray_dev_names.setter
    def subarray_dev_names(self, value: List[str]) -> None:
        """
        Input parameter
        Set the SubarrayNode device names to be
        managed by the CentralNode

        :param value: the SubarrayNode device names
        :type value: List
        """
        self._subarray_dev_names = value
        if self._changed_callback is not None:
            self._changed_callback()

    def update(self, component_manager) -> List[str]:
        """Update method for input parameter"""
        list_dev_names: List[str] = []
        for dev_name in self.subarray_dev_names:
            if component_manager.get_device(dev_name) is None:
                component_manager.add_device(dev_name)
                list_dev_names.append(dev_name)

        for dev_name in self.csp_subarray_dev_names:
            if component_manager.get_device(dev_name) is None:
                component_manager.add_device(dev_name)
                list_dev_names.append(dev_name)

        for dev_name in self.sdp_subarray_dev_names:
            if component_manager.get_device(dev_name) is None:
                component_manager.add_device(dev_name)
                list_dev_names.append(dev_name)

        dev_name = self.csp_master_dev_name
        if dev_name and component_manager.get_device(dev_name) is None:
            component_manager.add_device(dev_name)
            list_dev_names.append(dev_name)

        dev_name = self.csp_mln_dev_name
        if dev_name and component_manager.get_device(dev_name) is None:
            component_manager.add_device(dev_name)
            list_dev_names.append(dev_name)

        dev_name = self.sdp_master_dev_name
        if dev_name and component_manager.get_device(dev_name) is None:
            component_manager.add_device(dev_name)
            list_dev_names.append(dev_name)

        dev_name = self.sdp_mln_dev_name
        if dev_name and component_manager.get_device(dev_name) is None:
            component_manager.add_device(dev_name)
            list_dev_names.append(dev_name)
        return list_dev_names


class InputParameterLow(InputParameter):
    """Class for input parameter for low."""

    def __init__(self, changed_callback: Callable) -> None:
        super().__init__(changed_callback=changed_callback)
        self._subarray_dev_names = ["ska_low/tm_subarray_node/1"]
        self._csp_subarray_dev_names = ["ska_low/tm_leaf_node/csp_subarray01"]
        self._sdp_subarray_dev_names = ["ska_low/tm_leaf_node/sdp_subarray01"]
        self._csp_master_dev_name = "low-csp/control/0"
        self._sdp_master_dev_name = "low-sdp/control/0"
        self._mccs_master_dev_name = "low-mccs/control/control"
        self._sdp_mln_dev_name = "ska_low/tm_leaf_node/sdp_master"
        self._csp_mln_dev_name = "ska_low/tm_leaf_node/csp_master"
        self._mccs_mln_dev_name = "ska_low/tm_leaf_node/mccs_master"
        self._changed_callback = changed_callback

    @property
    def mccs_mln_dev_name(self):
        """
        Input parameter
        Return the MCCS Master Leaf Node device name

        :return: the MCCS Master Leaf Node device name
        :rtype: str
        """
        return self._mccs_mln_dev_name

    @mccs_mln_dev_name.setter
    def mccs_mln_dev_name(self, value):
        """
        Input parameter
        Set the MCCS Master Leaf Node device name to be
        managed by the CentralNode

        :param value: the MCCS Master Leaf Node device name
        :type value: str
        """
        self._mccs_mln_dev_name = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def mccs_master_dev_name(self):
        """
        Input parameter
        Return the MCCS Master device name

        :return: the MCCS Master device name
        :rtype: str
        """
        return self._mccs_master_dev_name

    @mccs_master_dev_name.setter
    def mccs_master_dev_name(self, value):
        """
        Input parameter
        Set the MCCS Master device name to be
        managed by the CentralNode

        :param value: the MCCS Master device name
        :type value: str
        """
        self._mccs_master_dev_name = value
        if self._changed_callback is not None:
            self._changed_callback()

    def update(self, component_manager):
        """Update method for input parameter"""
        list_dev_names = super().update(component_manager)
        dev_name = self.mccs_mln_dev_name
        if dev_name and component_manager.get_device(dev_name) is None:
            component_manager.add_device(dev_name)
            list_dev_names.append(dev_name)

        dev_name = self.mccs_master_dev_name
        if dev_name and component_manager.get_device(dev_name) is None:
            component_manager.add_device(dev_name)
            list_dev_names.append(dev_name)

        for devInfo in component_manager.devices:
            if devInfo.dev_name not in list_dev_names:
                component_manager.component.remove_device(devInfo.dev_name)


class InputParameterMid(InputParameter):
    """Class for Input parameter Mid this class is used to distinguish between
    between low and mid telescope"""

    def __init__(self, changed_callback: Callable) -> None:
        super().__init__(changed_callback=changed_callback)
        self._subarray_dev_names: List[str] = ["ska_mid/tm_subarray_node/1"]
        self._csp_subarray_dev_names: List[str] = [
            "ska_mid/tm_leaf_node/csp_subarray01"
        ]
        self._dish_leaf_node_dev_names: List[str] = [
            "ska_mid/tm_leaf_node/d0001"
        ]
        self._dish_dev_names: List[str] = ["ska001/elt/master"]
        self._sdp_subarray_dev_names: List[str] = [
            "ska_mid/tm_leaf_node/sdp_subarray01"
        ]
        self._csp_master_dev_name: str = "mid-csp/control/0"
        self._sdp_master_dev_name: str = "mid-sdp/control/0"
        self._sdp_mln_dev_name: str = "ska_mid/tm_leaf_node/sdp_master"
        self._csp_mln_dev_name: str = "ska_mid/tm_leaf_node/csp_master"
        self._dish_leaf_node_prefix: str = "ska_mid/tm_leaf_node/d0"
        self._dish_master_tag: str = "elt/master"
        self._changed_callback: Callable = changed_callback

    @property
    def dish_leaf_node_prefix(self) -> str:
        """
        Input parameter
        Return the TM dish prefix

        :return: the TM dish prefix
        :rtype: str
        """
        return self._dish_leaf_node_prefix

    @dish_leaf_node_prefix.setter
    def dish_leaf_node_prefix(self, value: str):
        """
        Input parameter
        Set the TM dish prefix to be
        managed by the CentralNode

        :param value: the TM dish prefix
        :type value: str
        """
        self._dish_leaf_node_prefix = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def dish_master_tag(self) -> str:
        """
        Input parameter
        Return the TMC dish master device tag

        :return: the TMC dish master device tag
        :rtype: str
        """
        return self._dish_master_tag

    @dish_master_tag.setter
    def dish_master_tag(self, value: str):
        """
        Input parameter
        Set the TMC dish master device tag to be
        managed by the CentralNode

        :param value: the TM dish master device tag
        :type value: str
        :return: : None
        :rtype: None

        """
        self._dish_master_tag = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def dish_leaf_node_dev_names(self) -> List[str]:
        """
        Input parameter
        Return the TM dish device names

        :return: the TM dish device names
        :rtype: List
        """
        return self._dish_leaf_node_dev_names

    @dish_leaf_node_dev_names.setter
    def dish_leaf_node_dev_names(self, value: List[str]):
        """
        Input parameter
        Set the TM dish device names to be
        managed by the CentralNode

        :param value: the TM dish device names
        :type value: list
        """
        self._dish_leaf_node_dev_names = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def dish_dev_names(self):
        """
        Input parameter
        Return the dish device names

        :return: the TM dish device names
        :rtype: tuple
        """
        return self._dish_dev_names

    @dish_dev_names.setter
    def dish_dev_names(self, value):
        """
        Input parameter
        Set the dish device names to be
        managed by the CentralNode

        :param value: the TM dish device names
        :type value: tuple
        """
        self._dish_dev_names = value
        if self._changed_callback is not None:
            self._changed_callback()

    def update(self, component_manager):
        """Update method for input parameters"""
        list_dev_names = super().update(component_manager)
        for dev_name in self.dish_leaf_node_dev_names:
            if component_manager.get_device(dev_name) is None:
                component_manager.add_device(dev_name)
                list_dev_names.append(dev_name)

        for dev_name in self.dish_dev_names:
            if component_manager.get_device(dev_name) is None:
                component_manager.add_device(dev_name)
                list_dev_names.append(dev_name)

        for devInfo in component_manager.devices:
            if devInfo.dev_name not in list_dev_names:
                component_manager.component.remove_device(devInfo.dev_name)

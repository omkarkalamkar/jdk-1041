class InputParameter:
    def __init__(self, changed_callback) -> None:
        self._tm_subarray_dev_names = ["ska_mid/tm_subarray_node/1"]
        self._csp_subarray_dev_names = ["ska_mid/tm_leaf_node/csp_subarray01"]
        self._tm_dish_dev_names = ["ska_mid/tm_leaf_node/d0001"]
        self._dish_dev_names = ["mid_d0001/elt/master"]
        self._sdp_subarray_dev_names = ["ska_mid/tm_leaf_node/sdp_subarray01"]
        self._csp_master_dev_name = "mid_csp/elt/master"
        self._sdp_master_dev_name = "mid_sdp/elt/master"
        self._tm_leaf_sdp_master_dev_name = "ska_mid/tm_leaf_node/sdp_master"
        self._tm_leaf_csp_master_dev_name = "ska_mid/tm_leaf_node/csp_master"
        self._changed_callback = changed_callback

    @property
    def tm_subarray_dev_names(self):
        """
        Input parameter
        Return the TM Subarray device names

        :return: the TM Subarray device names
        :rtype: tuple
        """
        return self._tm_subarray_dev_names

    @tm_subarray_dev_names.setter
    def tm_subarray_dev_names(self, value):
        """
        Input parameter
        Set the TM Subarray device names to be
        managed by the CentralNode

        :param value: the TM Subarray device names
        :type value: tuple
        """
        self._tm_subarray_dev_names = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def tm_dish_dev_names(self):
        """
        Input parameter
        Return the TM dish device names

        :return: the TM dish device names
        :rtype: tuple
        """
        return self._tm_dish_dev_names

    @tm_dish_dev_names.setter
    def tm_dish_dev_names(self, value):
        """
        Input parameter
        Set the TM dish device names to be
        managed by the CentralNode

        :param value: the TM dish device names
        :type value: tuple
        """
        self._tm_dish_dev_names = value
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

    @property
    def csp_subarray_dev_names(self):
        """
        Input parameter
        Return the CSP Subarray device names

        :return: the CSP Subarray device names
        :rtype: tuple
        """
        return self._csp_subarray_dev_names

    @csp_subarray_dev_names.setter
    def csp_subarray_dev_names(self, value):
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
    def sdp_subarray_dev_names(self):
        """
        Input parameter
        Return the SDP Subarray device names

        :return: the SDP Subarray device names
        :rtype: tuple
        """
        return self._sdp_subarray_dev_names

    @sdp_subarray_dev_names.setter
    def sdp_subarray_dev_names(self, value):
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
    def csp_master_dev_name(self):
        """
        Input parameter
        Return the CSP Master device name

        :return: the CSP Master device name
        :rtype: str
        """
        return self._csp_master_dev_name

    @csp_master_dev_name.setter
    def csp_master_dev_name(self, value):
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
    def sdp_master_dev_name(self):
        """
        Input parameter
        Return the SDP Master device name

        :return: the SDP Master device name
        :rtype: str
        """
        return self._sdp_master_dev_name

    @sdp_master_dev_name.setter
    def sdp_master_dev_name(self, value):
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
    def tm_leaf_csp_master_dev_name(self):
        """
        Input parameter
        Return the CSP Master device name

        :return: the CSP Master device name
        :rtype: str
        """
        return self._tm_leaf_csp_master_dev_name

    @tm_leaf_csp_master_dev_name.setter
    def tm_leaf_csp_master_dev_name(self, value):
        """
        Input parameter
        Set the CSP Master device name to be
        managed by the CentralNode

        :param value: the CSP Master device name
        :type value: str
        """
        self._tm_leaf_csp_master_dev_name = value
        if self._changed_callback is not None:
            self._changed_callback()

    @property
    def tm_leaf_sdp_master_dev_name(self):
        """
        Input parameter
        Return the SDP Master device name

        :return: the SDP Master device name
        :rtype: str
        """
        return self._tm_leaf_sdp_master_dev_name

    @tm_leaf_sdp_master_dev_name.setter
    def tm_leaf_sdp_master_dev_name(self, value):
        """
        Input parameter
        Set the SDP Master device name to be
        managed by the CentralNode

        :param value: the SDP Master device name
        :type value: str
        """
        self._tm_leaf_sdp_master_dev_name = value
        if self._changed_callback is not None:
            self._changed_callback()

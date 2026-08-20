"""Input Validator class for central node"""

# -*- coding: utf-8 -*-
#
# This file is part of the centralnode project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE for more info.

# standard Python imports
import json
import logging

from ska_tmc_cdm.exceptions import JsonValidationError, SchemaNotFound
from ska_tmc_cdm.messages.central_node.assign_resources import (
    AssignResourcesRequest,
)
from ska_tmc_cdm.messages.central_node.release_resources import (
    ReleaseResourcesRequest,
)

# SKA specific imports
from ska_tmc_cdm.schemas import CODEC
from ska_tmc_common.exceptions import (
    InvalidJSONError,
    InvalidReceptorIdError,
    ResourceNotPresentError,
    SubarrayNotPresentError,
)

module_logger = logging.getLogger(__name__)


class AssignResourceValidator:
    """Class to validate the input string of AssignResources command
    of Central Node"""

    def __init__(
        self,
        subarray_list,
        receptor_list,
        logger=module_logger,
        mkt_extension_id="",
        ska_dish_ranges: tuple = (1, 999),
        mkt_dish_ranges: tuple = (0, 63),
    ):
        self.logger = logger
        self._subarrays = []
        self._receptor_list = []
        self.mkt_extension_id = mkt_extension_id
        self.ska_dish_ranges = ska_dish_ranges
        self.mkt_dish_ranges = mkt_dish_ranges

        # get the ids of the numerical ids of available subarrays
        for subarray in subarray_list:
            tokens = subarray.split("/")
            self._subarrays.append(int(tokens[2]))
        self.logger.debug("Available subarray ids: %s", str(self._subarrays))

        # Populate the list of receptor ids from list of existing dishleaf node
        # FQDNs. The list is used later to search for any invalid receptor id
        # in AssignReources request JSON.
        for receptor in receptor_list:
            self._receptor_list.append(receptor.split("/")[-1].upper())
        self.logger.debug("Available dish ids: %s", str(self._receptor_list))

    def _subarray_exists(self, subarray_id):
        """Checks if subarray is present.

        :param: subarray_id: Integer

        :return: True if subarray exists. False if the subarray is not present.
        """
        ret_val = False
        self.logger.debug("Subarray ID: %d", subarray_id)
        if subarray_id not in self._subarrays:
            self.logger.debug("The subarray does not exist.")
        else:
            ret_val = True

        return ret_val

    def _search_invalid_receptors(self, receptor_id_list):
        """
        This method accepts the receptor id list from the AssignResources
        request. It searches
        each of the receptor id from this list into the list of receptors
        which are present in the
        system. The receptor ids that are not found in the list of present
        receptors are added in a
        list and returned to the caller.

        :param: receptor_id_list: List of strings for example
            ["SKA001", "SKA002", "MKT001"]

        :returns: List of receptors that do not exist. Empty list is returned
            when all receptors exist.
        """
        non_existing_receptors = []
        for receptor in receptor_id_list:
            if (receptor[:3] not in ["MKT", self.mkt_extension_id]) and (
                receptor not in self._receptor_list
            ):
                self.logger.debug("Receptor %s. is not present.", receptor)
                non_existing_receptors.append(receptor)
        self.logger.debug(
            "Invalid receptors identified from request: %s",
            non_existing_receptors,
        )
        return non_existing_receptors

    def _validate_and_get_assign_json(self, input_string: str) -> str:
        """Validates the assign input with CDM and provides the
        json if the format is correct.

        :param input_string: Input string.
        :type input_string: str
        :return: Assign json.
        :rtype: str
        """
        try:
            assign_request = CODEC.loads(AssignResourcesRequest, input_string)
            assign_json = CODEC.dumps(assign_request)
        except (
            JsonValidationError,
            SchemaNotFound,
            Exception,
        ) as json_error:
            self.logger.exception(
                "Exception occured while validating the json with cdm: %s",
                str(json_error),
            )
            exception_message = (
                "Malformed input string. Please check the JSON format."
                + "Full exception info: "
                + str(json_error)
            )
            raise InvalidJSONError(exception_message) from json_error
        return assign_json

    def _validate_subarray_id(self, subarray_id: int) -> None:
        """Validates if subarray exists.

        :param subarray_id: _description_
        :type subarray_id: int
        """
        if not self._subarray_exists(subarray_id):
            exception_message = (
                "The Subarray '" + str(subarray_id) + "' does not exist."
            )
            raise SubarrayNotPresentError(exception_message)
        self.logger.debug("SubarrayID validation successful.")

    def _syntatic_validation_dish_id(self, dish_id: str) -> None:
        """Performs syntatic validation of dish ID.

        :param dish_id: Dish ID.
        :type dish_id: str
        """
        if len(dish_id) != 6:
            exception_message = (
                f"The dish id {dish_id} is not of the correct length."
            )
            raise InvalidReceptorIdError(exception_message)
        if not dish_id[3:].isdigit():
            exp_msg = "The dish id {dish_id} not in correct format."
            raise InvalidReceptorIdError(exp_msg)
        if dish_id[:3] not in ["SKA", "MKT", self.mkt_extension_id]:
            exception_message = f"The dish prefix {dish_id} is invalid."
            raise InvalidReceptorIdError(exception_message)

    def _validate_dish_range(self, dish_id: str, dish_range: tuple) -> None:
        """Validates dish range as per range defined.

        :param dish_id: Dish ID.
        :type dish_id: str
        :param range: dish ID range tuple with (start, end)
        :type dish_id: str
        """
        dishid = int(dish_id[3:])
        if (dishid > dish_range[1]) or (dishid < dish_range[0]):
            exception_message = (
                f"The {dish_id[:3]} dish id {dish_id} is invalid."
            )
            raise InvalidReceptorIdError(exception_message)

    def _validate_receptors_not_empty(self, receptor_list: list[str]) -> None:
        """Validates if the receptor list is not empty.

        :param receptor_list: List of receptors
        :type receptor_list: list[str]
        """
        if not receptor_list:
            raise ValueError("Empty receptorIDList")

    def _validate_receptor_ids(self, receptor_list: list[str]) -> None:
        """Validate receptors IDs.
        :param receptor_list: List of receptors
        :type receptor_list: list[str]
        """
        for leaf_id in receptor_list:
            self._syntatic_validation_dish_id(leaf_id)
            if leaf_id.startswith("SKA"):
                self._validate_dish_range(leaf_id, self.ska_dish_ranges)
            if leaf_id.startswith("MKT"):
                self._validate_dish_range(leaf_id, self.mkt_dish_ranges)

    def _validate_receptors(self, receptor_list: list[str]) -> None:
        """Validates the receptors

        :param receptor_list: List of receptors
        :type receptor_list: list[str]
        """
        non_existing_receptors = self._search_invalid_receptors(receptor_list)
        if non_existing_receptors:
            exception_message = (
                "The following Receptor id(s) do not exist: "
                + str(non_existing_receptors)
            )
            raise ResourceNotPresentError(exception_message)
        self.logger.debug("Receptor ID list validation successful.")

    def loads(self, input_string: str) -> dict:
        """
        Validates the input string received as an argument of AssignResources
        command. If the request is correct, returns the deserialized JSON
        object. The ska-tmc-cdm is used to validate the JSON.

        Args:
            input_string (str): A JSON string

        Returns:
            dict: Deserialized JSON object if successful.

        Raises:
            InvalidJSONError: When the JSON string is not formatted properly.

            SubarrayNotPresentError: If the subarray is not present.

            ResourceNotPresentError: When a receptor in the
                receptor_id_list is not present.

        """
        assign_json = self._validate_and_get_assign_json(input_string)
        assign_request = json.loads(assign_json)
        self._validate_subarray_id(assign_request["subarray_id"])
        receptor_list = assign_request["dish"]["receptor_ids"]
        self._validate_receptors_not_empty(receptor_list)
        # Validate the receptor IDs to be in the correct format.
        # The expected format is 'SKAnnn' or 'MKTnnn'.
        # SKA nnn is a 3 digit number in range 001 to 133.
        # MKT nnn is a 3 digit number in range 000 to 063.
        self._validate_receptor_ids(receptor_list)
        self._validate_receptors(receptor_list)
        return assign_request


class ReleaseResourceValidator:
    """Class to validate the input string of ReleaseResources command
    of Central Node"""

    def __init__(self, logger=module_logger):
        self.logger = logger

    def loads(self, input_string: str):
        """
        Validates the input string received as an argument of ReleaseResources
        command.
        If the request is correct, returns the deserialized JSON object.
        The ska-tmc-cdm
        is used to validate the JSON.

        Args:
            input_string (str): A JSON string

        Returns:
            dict: Deserialized JSON object if successful.

        Raises:
            InvalidJSONError: When the JSON string is not formatted properly.

            SubarrayNotPresentError: If the subarray is not present.

            ResourceNotPresentError: When a receptor in the receptor_id_list
                is not present.

        """

        # Check if JSON is correct
        try:
            r_request = CODEC.loads(ReleaseResourcesRequest, input_string)
            release_json = CODEC.dumps(r_request)
        except (
            JsonValidationError,
            SchemaNotFound,
            Exception,
        ) as json_error:
            self.logger.exception(
                self.logger.exception("Exception: %s", str(json_error))
            )
            exception_message = (
                "Malformed input string. Please check the JSON format."
                + "Full exception info: "
                + str(json_error)
            )
            raise InvalidJSONError(exception_message) from json_error
        release_request = json.loads(release_json)
        return release_request

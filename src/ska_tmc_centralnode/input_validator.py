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
        dish_leaf_node_prefix,
        logger=module_logger,
    ):
        self.logger = logger
        self._subarrays = []
        self._receptor_list = []

        # get the ids of the numerical ids of available subarrays
        for subarray in subarray_list:
            tokens = subarray.split("/")
            self._subarrays.append(int(tokens[2]))
        self.logger.debug("Available subarray ids: %s", str(self._subarrays))

        # Populate the list of receptor ids from list of existing dishleaf node
        # FQDNs. The list is used later to search for any invalid receptor id
        # in AssignReources request JSON.
        for receptor in receptor_list:
            self._receptor_list.append(
                receptor.replace(dish_leaf_node_prefix, "SKA")
            )
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
            if (receptor[:3] != "MKT") and (
                receptor not in self._receptor_list
            ):
                self.logger.debug("Receptor %s. is not present.", receptor)
                non_existing_receptors.append(receptor)
        self.logger.debug(non_existing_receptors)
        return non_existing_receptors

    def loads(self, input_string):
        """
        Validates the input string received as an argument of AssignResources
        command. If the request is correct, returns the deserialized JSON
        object. The ska-tmc-cdm is used to validate the JSON.

        :param: input_string: A JSON string

        :return: Deserialized JSON object if successful.

        :throws:
            InvalidJSONError: When the JSON string is not formatted properly.

            SubarrayNotPresentError: If the subarray is not present.

            ResourceNotPresentError: When a receptor in the
            receptor_id_list is not present.
        """

        try:
            assign_request = CODEC.loads(AssignResourcesRequest, input_string)
            assign_json = CODEC.dumps(assign_request)
        except (
            JsonValidationError,
            SchemaNotFound,
            ValueError,
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

        # Validate subarray ID
        # TODO: Use the object returned by cdm library instead of parsing
        # JSON string.
        assign_request = json.loads(assign_json)
        if not self._subarray_exists(assign_request["subarray_id"]):
            exception_message = (
                "The Subarray '"
                + str(assign_request["subarray_id"])
                + "' does not exist."
            )
            raise SubarrayNotPresentError(exception_message)
        self.logger.debug("SubarrayID validation successful.")

        # Validate receptorIDList
        try:
            receptor_list = assign_request["dish"]["receptor_ids"]
            assert len(receptor_list) > 0
        except AssertionError as assertion_error:
            raise ValueError("Empty receptorIDList") from assertion_error

        # Validate the receptor IDs to be in the correct format.
        # The expected format is 'SKAnnn' or 'MKTnnn'.
        # SKA nnn is a 3 digit number in range 001 to 133.
        # MKT nnn is a 3 digit number in range 000 to 063.
        for leaf_id in receptor_list:
            if len(leaf_id) != 6:
                exception_message = (
                    f"The dish id {leaf_id} is not of the correct length."
                )
                raise InvalidReceptorIdError(exception_message)
            if not leaf_id[3:].isdigit():
                exp_msg = "The dish id {leaf_id} not in correct format."
                raise InvalidReceptorIdError(exp_msg)
            if leaf_id[:3] not in ["SKA", "MKT"]:
                exception_message = f"The dish prefix {leaf_id} is invalid."
                raise InvalidReceptorIdError(exception_message)
            if leaf_id[:3] == "SKA":
                if int(leaf_id[3:]) not in range(1, 134):
                    exception_message = (
                        f"The SKA dish id {leaf_id} is invalid."
                    )
                    raise InvalidReceptorIdError(exception_message)
            if leaf_id[:3] == "MKT":
                if int(leaf_id[3:]) not in range(0, 64):
                    exception_message = (
                        f"The MKT dish id {leaf_id} is invalid."
                    )
                    raise InvalidReceptorIdError(exception_message)

        non_existing_receptors = self._search_invalid_receptors(
            assign_request["dish"]["receptor_ids"]
        )
        if non_existing_receptors:
            exception_message = (
                "The following Receptor id(s) do not exist: "
                + str(non_existing_receptors)
            )
            raise ResourceNotPresentError(exception_message)
        self.logger.debug("Receptor ID list validation successful.")

        return assign_request


class ReleaseResourceValidator:
    """Class to validate the input string of ReleaseResources command
    of Central Node"""

    def __init__(self, logger=module_logger):
        self.logger = logger

    def loads(self, input_string):
        """
        Validates the input string received as an argument of ReleaseResources
        command.
        If the request is correct, returns the deserialized JSON object.
        The ska-tmc-cdm
        is used to validate the JSON.

        :param: input_string: A JSON string

        :return: Deserialized JSON object if successful.

        :throws:
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
            ValueError,
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

# pylint: disable=unused-variable,W0612
# flake8: noqa
# standard python imports
import json
from os.path import dirname, join

import pytest
from ska_tmc_common.exceptions import (
    InvalidJSONError,
    ResourceNotPresentError,
    ResourceReassignmentError,
    SubarrayNotPresentError,
)

# other imports
from ska_tmc_centralnode.input_validator import AssignResourceValidator

# Sample 'good' JSON

sample_assign_resources_request = {
    "interface": "https://schema.skao.int/ska-tmc-assignresources/2.0",
    "transaction_id": "txn-....-00001",
    "subarray_id": 1,
    "dish": {"receptor_ids": ["0001"]},
    "sdp": {
        "interface": "https://schema.skao.int/ska-sdp-assignres/0.3",
        "eb_id": "eb-mvp01-20200325-00001",
        "max_length": 100.0,
        "scan_types": [
            {
                "scan_type_id": "science_A",
                "reference_frame": "ICRS",
                "ra": "02:42:40.771",
                "dec": "-00:00:47.84",
                "channels": [
                    {
                        "count": 744,
                        "start": 0,
                        "stride": 2,
                        "freq_min": 0.35e9,
                        "freq_max": 0.368e9,
                        "link_map": [[0, 0], [200, 1], [744, 2], [944, 3]],
                    },
                    {
                        "count": 744,
                        "start": 2000,
                        "stride": 1,
                        "freq_min": 0.36e9,
                        "freq_max": 0.368e9,
                        "link_map": [[2000, 4], [2200, 5]],
                    },
                ],
            },
            {
                "scan_type_id": "calibration_B",
                "reference_frame": "ICRS",
                "ra": "12:29:06.699",
                "dec": "02:03:08.598",
                "channels": [
                    {
                        "count": 744,
                        "start": 0,
                        "stride": 2,
                        "freq_min": 0.35e9,
                        "freq_max": 0.368e9,
                        "link_map": [[0, 0], [200, 1], [744, 2], [944, 3]],
                    },
                    {
                        "count": 744,
                        "start": 2000,
                        "stride": 1,
                        "freq_min": 0.36e9,
                        "freq_max": 0.368e9,
                        "link_map": [[2000, 4], [2200, 5]],
                    },
                ],
            },
        ],
        "processing_blocks": [
            {
                "pb_id": "pb-mvp01-20200325-00001",
                "workflow": {
                    "kind": "realtime",
                    "name": "vis_receive",
                    "version": "0.1.0",
                },
                "parameters": {},
            },
            {
                "pb_id": "pb-mvp01-20200325-00002",
                "workflow": {
                    "kind": "realtime",
                    "name": "test_realtime",
                    "version": "0.1.0",
                },
                "parameters": {},
            },
            {
                "pb_id": "pb-mvp01-20200325-00003",
                "workflow": {
                    "kind": "batch",
                    "name": "ical",
                    "version": "0.1.0",
                },
                "parameters": {},
                "dependencies": [
                    {
                        "pb_id": "pb-mvp01-20200325-00001",
                        "kind": ["visibilities"],
                    }
                ],
            },
            {
                "pb_id": "pb-mvp01-20200325-00004",
                "workflow": {
                    "kind": "batch",
                    "name": "dpreb",
                    "version": "0.1.0",
                },
                "parameters": {},
                "dependencies": [
                    {
                        "pb_id": "pb-mvp01-20200325-00003",
                        "kind": ["calibration"],
                    }
                ],
            },
        ],
    },
}


class TestAssignResourceValidator:
    """Class to test the AssignResourceValidator class methods"""

    _test_subarray_list = [
        "test/subarray/1",
        "test/subarray/2",
        "test/subarray/3",
    ]
    _test_receptor_id_list = [
        "ska_mid/tm_leaf_node/d0001",
        "ska_mid/tm_leaf_node/d0002",
        "ska_mid/tm_leaf_node/d0003",
        "ska_mid/tm_leaf_node/d0004",
    ]

    # @pytest.mark.skip(reason="New JSON changes to be updated")
    def test_validate_good_json(self):
        """This function tests the validate method when good formatted json is provided"""

        input_validator = AssignResourceValidator(
            self._test_subarray_list,
            self._test_receptor_id_list,
            "ska_mid/tm_leaf_node/d",
        )
        output_config = input_validator.loads(
            json.dumps(sample_assign_resources_request)
        )
        assert output_config == sample_assign_resources_request

    # @pytest.mark.skip(reason="New JSON changes to be updated")
    def test_validate_wrong_subarray_id(self):
        """
        Tests that InvalidJSONError is raised when a wrong subarray id is given
        in the input string.
        """

        # Set wrong subarray id.
        input_json = sample_assign_resources_request
        input_json["subarray_id"] = 99

        input_validator = AssignResourceValidator(
            self._test_subarray_list,
            self._test_receptor_id_list,
            "ska_mid/tm_leaf_node/d",
        )

        with pytest.raises(SubarrayNotPresentError) as excinfo:
            input_validator.loads(json.dumps(input_json))

    # @pytest.mark.skip(reason="Behavior of this test case has changed in tox env.")
    def test_validate_incorrect_receptor_id(self):
        """
        Tests that ResourceNotPresentError is raised when a receptor id is given incorrect
        value in the input string.
        """

        input_json = sample_assign_resources_request
        invalid_receptor_id_list = ["9999"]
        input_json["dish"]["receptor_ids"] = invalid_receptor_id_list

        input_validator = AssignResourceValidator(
            self._test_subarray_list,
            self._test_receptor_id_list,
            "ska_mid/tm_leaf_node/d",
        )

        with pytest.raises(ResourceNotPresentError) as excinfo:
            input_validator.loads(json.dumps(input_json))

"""Test cases file"""

from ska_tmc_centralnode.utils.config_json_validator import DishConfigValidator
from tests.settings import create_cm


class TestDishConfigValidator:
    """Implement test cases to validate Dish Config
    Json
    """

    def test_valid_dish_config_json(self):
        """Validate Correct Dish Config json"""
        cm = create_cm()
        dish_config_json = {
            "interface": (
                "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2"
            ),
            "dish_parameters": {
                "SKA001": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1127},
                "SKA133": {"vcc": 4, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(
            dish_config_json, 1, 1177, cm.validate_dish_ids
        )
        is_valid, msg = dish_config_validator.is_json_valid()
        assert is_valid is True

    def test_dish_config_validator_for_invalid_dishids(self):
        """Validate Dish Config Json validator when dish ids are invalid"""
        cm = create_cm()
        dish_config_json = {
            "interface": (
                "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2"
            ),
            "dish_parameters": {
                "ABC001": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1127},
                "SKA133": {"vcc": 4, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(
            dish_config_json, 1, 1177, cm.validate_dish_ids
        )
        is_valid, msg = dish_config_validator.is_json_valid()
        assert is_valid is False
        assert msg == "Invalid Dish id ABC001 provided in Json"

    def test_dish_config_validator_for_invalid_dishids_range(self):
        """Validate Dish Config Json validator when dish ids
        are not within range"""
        cm = create_cm()
        dish_config_json = {
            "interface": (
                "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2"
            ),
            "dish_parameters": {
                "SKA1000": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1127},
                "SKA133": {"vcc": 4, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(
            dish_config_json, 1, 1177, cm.validate_dish_ids
        )
        is_valid, msg = dish_config_validator.is_json_valid()
        assert is_valid is False
        assert msg == "Dish id SKA1000 not in range (1,999)"

    def test_dish_config_validator_for_duplicate_vcc_ids(self):
        """Validate Dish Config Json validator when vcc ids are not unique"""
        cm = create_cm()
        dish_config_json = {
            "interface": (
                "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2"
            ),
            "dish_parameters": {
                "SKA001": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1127},
                "SKA101": {"vcc": 1, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(
            dish_config_json, 1, 1177, cm.validate_dish_ids
        )
        is_valid, msg = dish_config_validator.is_json_valid()
        assert is_valid is False
        assert msg == "Duplicate Vcc ids found in json"

    def test_invalid_k_value_exceeds_range(self):
        """Test case for invalid k value exceeding the range"""
        cm = create_cm()
        dish_config_json = {
            "interface": (
                "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2"
            ),
            "dish_parameters": {
                "SKA001": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1178},
                "SKA133": {"vcc": 4, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(
            dish_config_json, 1, 1177, cm.validate_dish_ids
        )
        is_valid, msg = dish_config_validator.is_json_valid()
        assert is_valid is False
        assert msg == "K values are not in range (1 to 1177)"

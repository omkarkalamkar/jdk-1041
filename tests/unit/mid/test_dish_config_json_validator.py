from ska_tmc_centralnode.utils.config_json_validator import DishConfigValidator


class TestDishConfigValidator:
    """Implement test cases to validate Dish Config
    Json
    """

    def test_valid_dish_config_json(self):
        """Validate Correct Dish Config json"""
        dish_config_json = {
            "interface": "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2",
            "dish_parameters": {
                "SKA001": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1127},
                "SKA133": {"vcc": 4, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(dish_config_json)
        assert dish_config_validator.is_json_valid() is True

    def test_dish_config_validator_for_invalid_dishids(self):
        """Validate Dish Config Json validator when dish ids are invalid"""
        dish_config_json = {
            "interface": "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2",
            "dish_parameters": {
                "ABC001": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1127},
                "SKA133": {"vcc": 4, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(dish_config_json)
        assert dish_config_validator.is_json_valid() is False

    def test_dish_config_validator_for_invalid_dishids_range(self):
        """Validate Dish Config Json validator when dish ids are not within range"""
        dish_config_json = {
            "interface": "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2",
            "dish_parameters": {
                "SKA187": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1127},
                "SKA133": {"vcc": 4, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(dish_config_json)
        assert dish_config_validator.is_json_valid() is False

    def test_dish_config_validator_for_duplicate_vcc_ids(self):
        """Validate Dish Config Json validator when vcc ids are not unique"""
        dish_config_json = {
            "interface": "https://schema.skao.int/ska-mid-cbf-initial-parameters/2.2",
            "dish_parameters": {
                "SKA001": {"vcc": 1, "k": 11},
                "SKA100": {"vcc": 2, "k": 101},
                "SKA036": {"vcc": 3, "k": 1127},
                "SKA101": {"vcc": 1, "k": 620},
            },
        }
        dish_config_validator = DishConfigValidator(dish_config_json)
        assert dish_config_validator.is_json_valid() is False

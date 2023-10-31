class DishConfigValidator:
    """This class implement method to validate DishConfig json"""

    def __init__(self, dish_config_json: dict):
        """
        params:
        dish_config_json(dict): Dish Config Json
        """
        self.dish_config_json = dish_config_json

    def _get_vcc_k_values(self):
        """Extract vcc and k values from dish config"""
        vcc_ids, k_values = [], []
        for _, vcc_k_map in self.dish_config_json["dish_parameters"].items():
            vcc_id = vcc_k_map.get("vcc")
            k_value = vcc_k_map.get("k")
            vcc_ids.append(vcc_id)
            k_values.append(k_value)
        return vcc_ids, k_values

    def _is_valid_k_values(self, k_values: list) -> bool:
        """Check if k values are within 1, 2223 range
        :params k_values: List of k values to validate
        """
        k_value_range = range(1, 2223)
        if all(k_value in k_value_range for k_value in k_values):
            return True, ""
        else:
            return False, "K values are not in range (1 to 2222)"

    def _is_valid_vcc_ids(self, vcc_ids: list) -> bool:
        """
        params:
        vcc_ids(list): List of VCC ids
        """
        if len(vcc_ids) == len(set(vcc_ids)):
            return True, ""
        else:
            return False, "Duplicate Vcc ids found in json"

    def _is_valid_dish_ids(self, dish_id_list: list) -> bool:
        """Validate Dish Ids are unique and validate
        Dish Id are within valid range
        """
        # Check if values are unique
        if len(dish_id_list) != len(set(dish_id_list)):
            return False, "Duplicate dish ids found in Json"

        # Check if dish id are within valid range
        for dish_id in dish_id_list:
            if dish_id.startswith("SKA"):
                dish_suffix = int(dish_id[3:])
                if dish_suffix not in range(1, 134):
                    return False, f"Dish id {dish_id} not in range (1,133)"
            elif dish_id.startswith("MKT"):
                dish_suffix = int(dish_id[3:])
                if dish_suffix not in range(1, 64):
                    return False, f"MKT id {dish_id} not in range (1,63)"
            else:
                return False, f"Invalid Dish id {dish_id} provided in Json"
        return True, ""

    def is_json_valid(self) -> bool:
        """This methid validate json as per following rules
        1. DishIDs are valid dishIDs (SKA001-133, MKT000-063)
        2. DishIDs are unique
        3. vcc_ids are unique
        4. valid range of k values (integer in the range 1-2222)
        5. valid range of vcc_ids

        Sample Json: "dish_parameters": {
                "SKA001": {
                    "vcc": 1,
                    "k"  : 11
                },
                "SKA100": {
                    "vcc": 2,
                    "k"  : 101
                },
                "SKA036": {
                    "vcc": 3,
                    "k"  : 1127
                },
                "SKA063": {
                    "vcc": 4,
                    "k"  : 620
                }
            }
        """
        dish_parameters = self.dish_config_json.get("dish_parameters")
        dish_ids = dish_parameters.keys()
        vcc_ids, k_values = self._get_vcc_k_values()

        is_valid_dish_id, message = self._is_valid_dish_ids(dish_ids)
        if not is_valid_dish_id:
            return is_valid_dish_id, message

        is_valid_vcc_ids, message = self._is_valid_vcc_ids(vcc_ids)
        if not is_valid_vcc_ids:
            return is_valid_vcc_ids, message

        is_valid_k_values, message = self._is_valid_k_values(k_values)
        if not is_valid_k_values:
            return is_valid_k_values, message

        return True, ""

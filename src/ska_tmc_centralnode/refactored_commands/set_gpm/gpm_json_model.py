"""Module to maintain the GPM Json model.
"""

import re
from typing import Dict, List, Literal

from pydantic import field_validator
from pydantic.dataclasses import dataclass


@dataclass
class GPMJsonModel:
    """Model for GPM validation"""

    version: str
    receptors: Dict[
        str,
        List[
            Literal[
                "Band_1",
                "Band_2",
                "Band_3",
                "Band_4",
                "Band_5a",
                "Band_5b",
                "band_1",
                "band_2",
                "band_3",
                "band_4",
                "band_5a",
                "band_5b",
            ]
        ],
    ]

    @field_validator("receptors")
    @classmethod
    def validate_receptor_keys(
        cls, receptors: Dict[str, list]
    ) -> Dict[str, list]:
        """Validates the receptor keys

        :param receptors: Receptors in the json.
        :type receptors: Dict[str, list]
        :raises ValueError: Raises value error if the value is incorrect.
        :return: Returns receptors data after validation
        :rtype: Dict[str, list]
        """
        if not receptors:
            raise ValueError("Please add receptors")
        cls.validate_dish_ids(list(receptors.keys()))
        return receptors

    @field_validator("receptors")
    @classmethod
    def validate_dish_ids(cls, dish_ids: list) -> list:
        """Validates the dish IDs

        :param dish_ids: Dish IDs in the json.
        :type dish_ids: list
        :raises ValueError: Raises value error if the value is incorrect.
        :return: Returns dish IDs after validation
        :rtype: list
        """
        pattern = r"^ska(\d{3})$"  # allow any three digits
        pattern2 = r"^mkt(\d{3})$"  # allow any three digits
        pattern3 = r"^mke(\d{3})$"  # allow any three digits
        for dish in dish_ids:
            dish = dish.lower()
            match = re.fullmatch(pattern, dish)
            match2 = re.fullmatch(pattern2, dish)
            match3 = re.fullmatch(pattern3, dish)
            if not (match or match2 or match3):
                raise ValueError(
                    f"Invalid dish '{dish}': does not match pattern '{pattern}' or '{pattern2}' or '{pattern3}'"
                )
        return dish_ids

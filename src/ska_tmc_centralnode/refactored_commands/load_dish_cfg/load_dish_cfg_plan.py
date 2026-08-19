from dataclasses import dataclass


@dataclass(slots=True)
class LoadDishCfgPlan:
    """
    Execution plan produced by LoadDishCfgStrategy.
    """

    dish_cfg_params: str
    dish_vcc_config_json: dict
    dish_parameters: dict

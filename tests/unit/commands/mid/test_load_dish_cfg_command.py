import pytest
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from tests.settings import create_cm, logger


@pytest.mark.test
def test_load_dish_cfg_command(tango_context, task_callback, json_factory):
    logger.info("%s", tango_context)
    cm, _ = create_cm()
    cm.is_command_allowed("LoadDishCfg")
    dish_cfg_input_str = json_factory("command_load_dish_cfg")

    cm.load_dish_cfg(dish_cfg_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )

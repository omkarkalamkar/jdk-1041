from ska_tango_base.commands import BaseCommand, ResultCode

class On(BaseCommand):
    """
    A class for CentralNode's On() command.

    On command on Central node enables the TMC to perform further operations
    and observations. It Invokes On command on TMC devices.

    """

    RESULT_MESSAGES = {
        ResultCode.OK: "ON command completed OK",
        ResultCode.FAILED: "ON command failed",
    }

    def __init__(self, target, *args, logger=None, **kwargs):
        """
        Initialise a new On command instance.
        """
        super().__init__(target, args, logger, kwargs)


    def do(self):
        """
        Call the on methods in all adapters.
        """
        component_manager = self.target
        result_code = ResultCode.OK
        for adapter in component_manager.adapters:
            try:
                adapter.On()
            except Exception as e:
                result_code = ResultCode.FAILED
                self.logger.error("Exception in calling on command on device: %s", adapter.dev_name)
                self.logger.error("Exception: %s", e)

        return (result_code, self.RESULT_MESSAGES[result_code])

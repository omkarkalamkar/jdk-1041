from ska_tango_base.commands import BaseCommand, ResultCode

class Off(BaseCommand):
    """
    A class for CentralNode's Off() command.

    Off command on Central node disable the TMC to perform further operations
    and observations. 
    It Invokes Off command on TMC devices.
    """

    
    RESULT_MESSAGES = {
        ResultCode.OK: "OFF command completed OK",
        ResultCode.FAILED: "OFF command failed",
    }

    def __init__(self, target, *args, logger=None, **kwargs):
        """
        Initialise a new On command instance.
        """
        super().__init__(target, args, logger, kwargs)


    def do(self):
        """
        Call the on methods in all adapters.

        what if we need an order of the Off commands to be sent?
        Should we wait here?
        """
        component_manager = self.target
        result_code = ResultCode.OK
        for adapter in component_manager.adapters:
            try:
                adapter.Off()
            except Exception as e:
                result_code = ResultCode.FAILED
                self.logger.error("Exception in calling on command on device: %s", adapter.dev_name)
                self.logger.error("Exception: %s", e)

        return (result_code, self.RESULT_MESSAGES[result_code])
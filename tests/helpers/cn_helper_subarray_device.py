# Note: This helper class module is explicitly required for CentralNode. Hence kept it here and not in ska-tmc-common repo.


from ska_tango_base.commands import ResultCode
from ska_tmc_common.test_helpers.helper_subarray_device import (
    HelperSubArrayDevice,
)
from tango import AttrWriteType
from tango.server import attribute, command


class CNHelperSubArrayDevice(HelperSubArrayDevice):
    """A generic device for triggering state changes with a command"""

    def init_device(self):
        super().init_device()
        self._is_subarray_available = False

    class InitCommand(HelperSubArrayDevice.InitCommand):
        def do(self):
            super().do()
            self._device.set_change_event("isSubarrayAvailable", True, False)

            return (ResultCode.OK, "")

    isSubarrayAvailable = attribute(
        dtype="DevBoolean", access=AttrWriteType.READ
    )

    def read_isSubarrayAvailable(self) -> bool:
        """Returns subarray availability in boolean format."""
        return self._is_subarray_available

    @command(
        dtype_in="DevBoolean",
        doc_in="Set subarray's availability",
    )
    def SetisSubarrayAvailable(self, value: bool) -> None:
        """This method sets subarray availability in boolean format."""
        if self._is_subarray_available != value:
            self.logger.info("Setting the subarray availability : %s", value)
            self._is_subarray_available = value
            try:
                self.push_change_event(
                    "isSubarrayAvailable", self._is_subarray_available
                )
            except Exception as exception:
                self.logger.exception(f"Error pushing the event. {exception}")

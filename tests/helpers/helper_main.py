from tango.server import run
from tests.helpers.helper_state_device import HelperStateDevice
from tests.helpers.helper_state_mccsdevice import HelperMCCSStateDevice
from tests.helpers.helper_subarray_device import HelperSubArrayDevice

def main(args=None, **kwargs):
    """
    Runs the a multiclass TANGO Device server which 
    includes all Helper classes classes.
    :param args: Arguments internal to TANGO

    :param kwargs: Arguments internal to TANGO

    :return: Multi class TANGO object.
    """
    return run((HelperSubArrayDevice,HelperStateDevice,HelperMCCSStateDevice), args=args, **kwargs)


if __name__ == "__main__":
    main()
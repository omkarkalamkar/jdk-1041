"""
aggregator class for CentralNode.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import logging

# Tango imports
import tango
from tango import DevFailed

# Additional import


# PROTECTED REGION END #    //  CentralNode.additional_import



class Aggregator:
    """
    Aggregator class is an abstract class for state event subscription and state
    callback.
    """
    
    def __init__(self, logger=None):
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger


    def subscribe_event(self):
        """
        Method for event subscription. Calls separate subscribe event methods for CSP Master, SDP Master and
        Subarray health state attribute subscription.
        """
        

    def unsubscribe_event(self):
        """
        Method to unsubscribe to health state change event on CspMasterLeafNode, SdpMasterLeafNode and SubarrayNode
        """

    
"""
aggregator class for CentralNode.
Note: The class should maintain a list. It will be used to maintain the devices of which state aggregation is to be done. Instead of a list,
a map can be implemented which may be used to maintain event ids of subscriptions etc.
"""
# PROTECTED REGION ID(CentralNode.additionnal_import) ENABLED START #
# Standard Python imports
import logging

# Tango imports
import tango
from tango import DevFailed


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
        Method for event subscription. Calls separate subscribe event methods for CSPMasterLeafNode, SDPMasterLeafNode, 
        TM Subarray, DishLeafNode, CSPSubarrayLeafNode, SDPSubarrayLeafNode state attribute subscription.
        """
        
    def unsubscribe_event(self):
        """
        Method to unsubscribe to state change event on CspMasterLeafNode, SdpMasterLeafNode,  CspSubarrayLeafNode, SdpSubarrayLeafNode, DishLeafNode and SubarrayNode
        """

    def aggregate(self):
        """
        Note: There should be methods to add and remove entries in the list. Subscribe/unsubscribe methods can be made internal to the class.
        The class should also have an abstract method called aggregate. The inherited classes can then overload/override it as per requirement.
        """
    
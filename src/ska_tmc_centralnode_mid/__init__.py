# -*- coding: utf-8 -*-
#
# This file is part of the CentralNode project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""CentralNode

Central Node is a coordinator of the complete M&C system.
"""

from ska_tmc_centralnode_mid import release
from ska_tmc_centralnode_mid.central_node import CentralNode
from ska_tmc_centralnode_mid import input_validator
from ska_tmc_centralnode_mid.dev_factory import DevFactory
__all__ = ["release", "CentralNode", "input_validator", "DevFactory"]

__version__ = release.version
__version_info__ = release.version_info
__author__ = release.author

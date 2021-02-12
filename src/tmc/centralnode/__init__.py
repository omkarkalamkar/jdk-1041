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

from tmc.centralnode import release
from tmc.centralnode import const
from tmc.centralnode.central_node import CentralNode
from tmc.centralnode import input_validator
from tmc.centralnode import exceptions
__all__ = ["release", "const", "CentralNode", "input_validator", "exceptions"]

__version__ = release.version
__version_info__ = release.version_info
__author__ = release.author

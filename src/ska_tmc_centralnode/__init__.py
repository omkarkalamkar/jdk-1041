# -*- coding: utf-8 -*-
#
# This file is part of the CentralNode project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE for more info.

"""CentralNode

Central Node is a coordinator of the complete M&C system.
"""

from ska_tmc_common.dev_factory import DevFactory

from ska_tmc_centralnode import input_validator, release

__all__ = ["release", "input_validator", "DevFactory"]

__version__ = release.version
__version_info__ = release.version_info
__author__ = release.author

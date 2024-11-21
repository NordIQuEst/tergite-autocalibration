# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
import os

import redis

from tergite_autocalibration.config.env import REDIS_PORT, PLOTTING, CONFIG_DIR
from tergite_autocalibration.config.handler import ConfigurationHandler
from tergite_autocalibration.config.package import ConfigurationPackage

REDIS_CONNECTION = redis.Redis(decode_responses=True, port=REDIS_PORT)

# This will be set in matplotlib
PLOTTING_BACKEND = "tkagg" if PLOTTING else "agg"

CONFIG = ConfigurationHandler.from_configuration_package(
    ConfigurationPackage.from_toml(os.path.join(CONFIG_DIR, "configuration.meta.toml"))
)

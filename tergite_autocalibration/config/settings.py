# This code is part of Tergite
#
# (C) Copyright Stefan Hill 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# ---
# This file contains all functionality related to the system settings and configuration.
# If you are adding variables, please make sure that they are upper case, because in the code, it should be
# clear that these variables are sort of global configuration environment variables

import getpass
import logging
import os
from ipaddress import ip_address
from pathlib import Path

from tergite_autocalibration.config.utils import from_environment

# ---
# Default prefix for paths
DEFAULT_PREFIX = from_environment(
    "DEFAULT_PREFIX",
    cast_=str,
    default=getpass.getuser().replace(" ", ""),
)

# ---
# Section with directory configurations

# Root directory of the project
ROOT_DIR = from_environment(
    "ROOT_DIR", cast_=Path, default=Path(__file__).parent.parent.parent
)

# Data directory to store plots and datasets
DATA_DIR = from_environment("DATA_DIR", cast_=Path, default=ROOT_DIR.joinpath("out"))

# If the data directory does not exist, it will be created automatically
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logging.info(f"Initialised DATA_DIR -> {DATA_DIR}")

# Path to the definition of the configuration package
CONFIG_DIR = from_environment("CONFIG_DIR", cast_=Path, default=ROOT_DIR)

BACKEND_CONFIG = Path(__file__).parent / "backend_config_default.toml"

# ---
# Section with other configuration variables
CLUSTER_IP = ip_address(from_environment("CLUSTER_IP", cast_=str))
SPI_SERIAL_PORT = from_environment("SPI_SERIAL_PORT", cast_=str)

# ---
# Section for redis connectivity
REDIS_PORT = from_environment("REDIS_PORT", cast_=int, default=6379)

# ---
# Section for plotting
PLOTTING = from_environment("PLOTTING", cast_=bool, default=False)


# ---
# Section with connectivity definitions
MSS_MACHINE_ROOT_URL = from_environment(
    "MSS_MACHINE_ROOT_URL", cast_=str, default="http://localhost:8002"
)

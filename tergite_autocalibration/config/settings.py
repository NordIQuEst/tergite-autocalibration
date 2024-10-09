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
import logging
import os
import typing
import warnings
from ipaddress import ip_address
from pathlib import Path

import redis
from dotenv import dotenv_values

T = typing.TypeVar("T")
config = dotenv_values(Path(__file__).parent.parent.parent.joinpath(".env"))


def _from_config(key_name_: str, cast_: type = str, default: T = None) -> T:
    """
    Helper function to read keys from the .env file

    Args:
        key_name_: Name of the variable to read from .env
        cast_: Cast variable to type T
        default: Default value for the variable (will be checked for type T)

    Returns:
        Type-checked-and-casted variable from .env

    """

    if os.environ.get(key_name_) is not None:
        try:
            if cast_ is bool:
                return eval(os.environ.get(key_name_))
            return cast_(os.environ.get(key_name_))
        except ValueError:
            raise ValueError(
                f"Variable with name {key_name_} from system environmental variables with value "
                f"{os.environ.get(key_name_)} cannot be casted to type {cast_}"
            )
    elif key_name_ in config:
        try:
            if cast_ is bool:
                return eval(config[key_name_])
            return cast_(config[key_name_])
        except ValueError:
            raise ValueError(
                f"Variable with name {key_name_} from .env with value {config[key_name_]} "
                f"cannot be casted to type {cast_}"
            )
    elif default is not None:
        # This is mainly a check for ourselves
        assert isinstance(default, cast_)
        return default
    else:
        warnings.warn(f"Cannot read {key_name_} from environment variables.")
        return None


# ---
# Default prefix for paths
DEFAULT_PREFIX = _from_config(
    "DEFAULT_PREFIX",
    cast_=str,
    default="calibration",
)

# ---
# Section with directory configurations

# Root directory of the project
ROOT_DIR = _from_config(
    "ROOT_DIR", cast_=Path, default=Path(__file__).parent.parent.parent
)

# Data directory to store plots and datasets
DATA_DIR = _from_config("DATA_DIR", cast_=Path, default=ROOT_DIR.joinpath("out"))

# If the data directory does not exist, it will be created automatically
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logging.info(f"Initialised DATA_DIR -> {DATA_DIR}")

# Configuration directory to store additional configuration files
CONFIG_DIR = _from_config(
    "CONFIG_DIR", cast_=Path, default=ROOT_DIR.joinpath("configs")
)

# ---
# Section with configuration files
HARDWARE_CONFIG = CONFIG_DIR.joinpath(_from_config("HARDWARE_CONFIG", cast_=Path))
SPI_CONFIG = CONFIG_DIR.joinpath(_from_config("SPI_CONFIG", cast_=Path))
DEVICE_CONFIG = CONFIG_DIR.joinpath(_from_config("DEVICE_CONFIG", cast_=Path))
CALIBRATION_CONFIG = CONFIG_DIR.joinpath(_from_config("CALIBRATION_CONFIG", cast_=Path))
QOI_CONFIG = CONFIG_DIR.joinpath(_from_config("QOI_CONFIG", cast_=Path))
USER_SAMPLESPACE = CONFIG_DIR.joinpath((_from_config("USER_SAMPLESPACE", cast_=Path)))
BACKEND_CONFIG = Path(__file__).parent / "backend_config_default.toml"

# ---
# Section with other configuration variables
CLUSTER_IP = ip_address(_from_config("CLUSTER_IP", cast_=str))
CLUSTER_NAME = _from_config("CLUSTER_NAME", cast_=str)
SPI_SERIAL_PORT = _from_config("SPI_SERIAL_PORT", cast_=str)

# ---
# Section for redis connectivity
REDIS_PORT = _from_config("REDIS_PORT", cast_=int, default=6379)
REDIS_CONNECTION = redis.Redis(decode_responses=True, port=REDIS_PORT)

# ---
# Section for plotting
PLOTTING = _from_config("PLOTTING", cast_=bool, default=False)
# This will be set in matplotlib
PLOTTING_BACKEND = "tkagg" if PLOTTING else "agg"


# ---
# Section with connectivity definitions
MSS_MACHINE_ROOT_URL = _from_config(
    "MSS_MACHINE_ROOT_URL", cast_=str, default="http://localhost:8002"
)

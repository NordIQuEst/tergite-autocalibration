# This code is part of Tergite
#
# (C) Copyright Eleftherios Moschandreou 2023, 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from os import walk

import xarray as xr

from tergite_autocalibration.config.env import DATA_DIR


def extract_ds_date(filename: str) -> int:
    # TODO use datetime module for proper datetime handling
    ym, day, time, node, tuid = filename.split("-", 4)
    date = int(ym + day + time)
    return date


def load_multiplexed_dataset(user_substr: str) -> xr.Dataset:
    _, _, filenames = next(walk(DATA_DIR))
    matched_list = list(filter(lambda x: user_substr in x, filenames))
    latest_file = max(matched_list, key=extract_ds_date)
    ds = xr.open_dataset(DATA_DIR / latest_file)
    return ds

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
from tergite_autocalibration.tests.utils.env import setup_test_env

setup_test_env()

from tergite_autocalibration.config.data import dh


def test_data_handler():
    assert "q06" in dh.device["qubit"].keys()


def test_data_handler_legacy():
    assert dh.get_legacy("VNA_resonator_frequencies")["q06"] == 6832973301.189378
    assert dh.get_legacy("VNA_qubit_frequencies")["q06"] == 4641051698.389338
    assert dh.get_legacy("VNA_f12_frequencies")["q06"] == 4.507e9

    assert dh.get_legacy("attenuation_setting")["qubit"] == 10
    assert dh.get_legacy("attenuation_setting")["coupler"] == 34
    assert dh.get_legacy("attenuation_setting")["resonator"] == 12

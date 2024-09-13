# This code is part of Tergite
#
# (C) Copyright Michele Faucci Giannelli 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import os
from pathlib import Path

import matplotlib
import numpy as np
import numpy.testing as npt
import pytest
import xarray as xr
from matplotlib import pyplot as plt

from tergite_autocalibration.lib.base.analysis import BaseAnalysis
from tergite_autocalibration.lib.nodes.coupler.cz_parametrisation.analysis import (
    FrequencyVsAmplitudeAnalysis,
    FrequencyVsAmplitudeQ1Analysis,
    FrequencyVsAmplitudeQ2Analysis,
)


@pytest.fixture(autouse=True)
def setup_good_data():
    os.environ["DATA_DIR"] = str(Path(__file__).parent / "results")
    dataset_path = Path(__file__).parent / "data" / "dataset_good_quality_freq_amp.hdf5"
    print(dataset_path)
    ds = xr.open_dataset(dataset_path)
    ds = ds.isel(ReIm=0) + 1j * ds.isel(ReIm=1)
    d14 = ds.yq14.to_dataset()
    d15 = ds.yq15.to_dataset()
    d14.yq14.attrs["qubit"] = "q14"
    d15.yq15.attrs["qubit"] = "q15"
    freqs = ds[f"cz_pulse_frequenciesq14_q15"].values  # MHz
    amps = ds[f"cz_pulse_amplitudesq14_q15"].values  # uA
    return d14, d15, freqs, amps


def test_canCreateCorrectClass(setup_good_data):
    d14, d15, freqs, amps = setup_good_data
    c = FrequencyVsAmplitudeQ1Analysis(d14, freqs, amps)
    assert isinstance(c, FrequencyVsAmplitudeQ1Analysis)
    assert isinstance(c, FrequencyVsAmplitudeAnalysis)
    assert isinstance(c, BaseAnalysis)
    c = FrequencyVsAmplitudeQ2Analysis(d15, freqs, amps)
    assert isinstance(c, FrequencyVsAmplitudeQ2Analysis)
    assert isinstance(c, FrequencyVsAmplitudeAnalysis)
    assert isinstance(c, BaseAnalysis)


def test_hasCorrectFreqsAndAmps(setup_good_data):
    d14, d15, freqs, amps = setup_good_data
    c14 = FrequencyVsAmplitudeQ1Analysis(d14, freqs, amps)
    npt.assert_array_equal(c14.frequencies, freqs)
    npt.assert_array_equal(c14.amplitudes, amps)
    c15 = FrequencyVsAmplitudeQ2Analysis(d15, freqs, amps)
    npt.assert_array_equal(c15.frequencies, freqs)
    npt.assert_array_equal(c15.amplitudes, amps)


def test_dataIsReadCorrectly(setup_good_data):
    d14, d15, freqs, amps = setup_good_data
    c14 = FrequencyVsAmplitudeQ1Analysis(d14, freqs, amps)
    npt.assert_array_equal(c14.dataset[f"y{c14.qubit}"].values, d14[f"yq14"].values)
    c15 = FrequencyVsAmplitudeQ2Analysis(d15, freqs, amps)
    npt.assert_array_equal(c15.dataset[f"y{c15.qubit}"].values, d15[f"yq15"].values)


def test_datasetHasQubitDefined(setup_good_data):
    d14, d15, freqs, amps = setup_good_data
    c = FrequencyVsAmplitudeQ1Analysis(d14, freqs, amps)
    assert c.qubit == "q14"
    c = FrequencyVsAmplitudeQ2Analysis(d15, freqs, amps)
    assert c.qubit == "q15"


def test_canGetMaxFromQ1(setup_good_data):
    d14, d15, freqs, amps = setup_good_data
    c = FrequencyVsAmplitudeQ1Analysis(d14, freqs, amps)
    result = c.analyse_qubit()
    indexBestFreq = np.where(freqs == result[0])[0]
    indexBestAmp = np.where(amps == result[1])[0]
    assert indexBestFreq[0] == 9
    assert indexBestAmp[0] == 13


def test_canGetMinFromQ2(setup_good_data):
    d14, d15, freqs, amps = setup_good_data
    c = FrequencyVsAmplitudeQ2Analysis(d15, freqs, amps)
    result = c.analyse_qubit()
    indexBestFreq = np.where(freqs == result[0])[0]
    indexBestAmp = np.where(amps == result[1])[0]
    assert indexBestFreq[0] == 10
    assert indexBestAmp[0] == 12


def test_canPlot(setup_good_data):
    matplotlib.use("Agg")
    d14, d15, freqs, amps = setup_good_data
    c14 = FrequencyVsAmplitudeQ1Analysis(d14, freqs, amps)
    result = c14.analyse_qubit()

    figure_path = os.environ["DATA_DIR"] + "/Frequency_Amplitude_q14.png"
    # Remove the file if it already exists
    if os.path.exists(figure_path):
        os.remove(figure_path)

    fig, ax = plt.subplots(figsize=(15, 7), num=1)
    plt.Axes
    c14.plotter(ax)
    fig.savefig(figure_path)
    plt.close()

    assert os.path.exists(figure_path)
    from PIL import Image

    with Image.open(figure_path) as img:
        assert img.format == "PNG", "File should be a PNG image"

    c15 = FrequencyVsAmplitudeQ2Analysis(d15, freqs, amps)
    result = c15.analyse_qubit()

    figure_path = os.environ["DATA_DIR"] + "/Frequency_Amplitude_q15.png"
    # Remove the file if it already exists
    if os.path.exists(figure_path):
        os.remove(figure_path)

    fig, ax = plt.subplots(figsize=(15, 7), num=1)
    plt.Axes
    c15.plotter(ax)
    fig.savefig(figure_path)
    plt.close()

    assert os.path.exists(figure_path)
    from PIL import Image

    with Image.open(figure_path) as img:
        assert img.format == "PNG", "File should be a PNG image"


@pytest.fixture(autouse=True)
def setup_bad_data():
    os.environ["DATA_DIR"] = str(Path(__file__).parent / "results")
    dataset_path = Path(__file__).parent / "data" / "dataset_bad_quality_freq_amp.hdf5"
    print(dataset_path)
    ds = xr.open_dataset(dataset_path)
    ds = ds.isel(ReIm=0) + 1j * ds.isel(ReIm=1)
    d14 = ds.yq14.to_dataset()
    d15 = ds.yq15.to_dataset()
    d14.yq14.attrs["qubit"] = "q14"
    d15.yq15.attrs["qubit"] = "q15"
    freqs = ds[f"cz_pulse_frequenciesq14_q15"].values  # MHz
    amps = ds[f"cz_pulse_amplitudesq14_q15"].values  # uA
    return d14, d15, freqs, amps


def test_canPlotBad(setup_bad_data):
    matplotlib.use("Agg")
    d14, d15, freqs, amps = setup_bad_data
    c14 = FrequencyVsAmplitudeQ1Analysis(d14, freqs, amps)
    result = c14.analyse_qubit()

    figure_path = os.environ["DATA_DIR"] + "/Frequency_Amplitude_bad_q14.png"
    # Remove the file if it already exists
    if os.path.exists(figure_path):
        os.remove(figure_path)

    fig, ax = plt.subplots(figsize=(15, 7), num=1)
    plt.Axes
    c14.plotter(ax)
    fig.savefig(figure_path)
    plt.close()

    assert os.path.exists(figure_path)
    from PIL import Image

    with Image.open(figure_path) as img:
        assert img.format == "PNG", "File should be a PNG image"

    c15 = FrequencyVsAmplitudeQ2Analysis(d15, freqs, amps)
    result = c15.analyse_qubit()

    figure_path = os.environ["DATA_DIR"] + "/Frequency_Amplitude_bad_q15.png"
    # Remove the file if it already exists
    if os.path.exists(figure_path):
        os.remove(figure_path)

    fig, ax = plt.subplots(figsize=(15, 7), num=1)
    plt.Axes
    c15.plotter(ax)
    fig.savefig(figure_path)
    plt.close()

    assert os.path.exists(figure_path)
    from PIL import Image

    with Image.open(figure_path) as img:
        assert img.format == "PNG", "File should be a PNG image"

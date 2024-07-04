import numpy as np

from tergite_autocalibration.config.settings import REDIS_CONNECTION
from tergite_autocalibration.lib.nodes.coupler.cz_chevron.cz_chevron_analysis import (
    CZChevronAnalysis,
    CZChevronAmplitudeAnalysis,
    CZChevronAnalysisReset,
)
from tergite_autocalibration.lib.nodes.coupler.cz_chevron.cz_firstStep_analysis import (
    CZFirtStepAnalysis,
)
from tergite_autocalibration.lib.base.node import BaseNode
from tergite_autocalibration.lib.nodes.coupler.cz_chevron.cz_chevron_reversed import (
    CZ_chevron,
    CZ_chevron_amplitude,
)
from tergite_autocalibration.lib.nodes.coupler.cz_calibration.measurement import Reset_calibration_SSRO


class CZ_Chevron_Node(BaseNode):
    measurement_obj = CZ_chevron
    analysis_obj = CZChevronAnalysis

    def __init__(
        self, name: str, all_qubits: list[str], couplers: list[str], **node_dictionary
    ):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.all_qubits = all_qubits
        self.couplers = couplers
        self.edges = couplers
        self.coupler = self.couplers[0]
        self.redis_field = ["cz_pulse_frequency", "cz_pulse_duration"]
        self.qubit_state = 0
        self.all_qubits = [q for bus in couplers for q in bus.split("_")]
        self.coupler_samplespace = self.samplespace
        try:
            print(f'{self.node_dictionary["cz_pulse_amplitude"] = }')
        except:
            amplitude = float(
                REDIS_CONNECTION.hget(f"couplers:{self.coupler}", "cz_pulse_amplitude")
            )
            print(f"Amplitude found for coupler {self.coupler} : {amplitude}")
            if np.isnan(amplitude):
                amplitude = 0.375
                print(
                    f"No amplitude found for coupler {self.coupler}. Using default value: {amplitude}"
                )
            self.node_dictionary["cz_pulse_amplitude"] = amplitude

        self.schedule_samplespace = {
            "cz_pulse_durations": {
                coupler: np.arange(0e-9, 401e-9, 20e-9) + 100e-9
                for coupler in self.couplers
            },
            "cz_pulse_frequencies": {
                coupler: np.linspace(-15e6, 10e6, 26)
                + self.transition_frequency(coupler)
                for coupler in self.couplers
            },
        }

        self.validate()

    def validate(self) -> None:
        all_coupled_qubits = []
        for coupler in self.couplers:
            all_coupled_qubits += coupler.split("_")
        if len(all_coupled_qubits) > len(set(all_coupled_qubits)):
            print("Couplers share qubits")
            raise ValueError("Improper Couplers")

    def transition_frequency(self, coupler: str):
        coupled_qubits = coupler.split(sep="_")
        q1_f01 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[0]}", "clock_freqs:f01")
        )
        q2_f01 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[1]}", "clock_freqs:f01")
        )
        q1_f12 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[0]}", "clock_freqs:f12")
        )
        q2_f12 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[1]}", "clock_freqs:f12")
        )
        # ac_freq = np.abs(q1_f01 + q2_f01 - (q1_f01 + q1_f12))
        ac_freq = np.max(
            [
                np.abs(q1_f01 + q2_f01 - (q1_f01 + q1_f12)),
                np.abs(q1_f01 + q2_f01 - (q2_f01 + q2_f12)),
            ]
        )
        ac_freq = int(ac_freq / 1e4) * 1e4
        # lo = 4.4e9 - (ac_freq - 450e6)
        # print(f'{ ac_freq/1e6 = } MHz for coupler: {coupler}')
        # print(f'{ lo/1e9 = } GHz for coupler: {coupler}')
        return ac_freq


class CZ_Characterisation_Chevron_Node(BaseNode):
    measurement_obj = CZ_chevron
    analysis_obj = CZFirtStepAnalysis

    def __init__(self, name: str, all_qubits: list[str], couplers: list[str]):
        super().__init__(name, all_qubits)
        self.type = "characterisation_sweep"
        self.couplers = couplers
        self.coupler = self.couplers[0]
        self.redis_field = [
            "cz_parking_current",
            "cz_pulse_amplitude",
            "cz_pulse_frequency",
            "cz_pulse_duration",
        ]
        self.optimization_field = (
            "cz_parking_current",
            "cz_pulse_amplitude",
            "cz_pulse_frequency",
            "cz_pulse_duration",
        )
        self.qubit_state = 0
        self.measurement_obj = CZ_chevron
        self.analysis_obj = CZFirtStepAnalysis
        self.all_qubits = [q for bus in couplers for q in bus.split("_")]
        self.coupler_samplespace = self.samplespace
        self.schedule_samplespace = {
            # For Wide sweep
            "cz_parking_current": {
                qubit: np.linspace(0.0008625, 0.0011625, 12)
                for qubit in self.coupled_qubits
            },
            "cz_pulse_amplitude": {
                qubit: np.linspace(0, 0.2, 3) for qubit in self.coupled_qubits
            },
            "cz_pulse_durations": {
                qubit: 80e-9 + np.arange(0e-9, 400e-9, 20e-9)
                for qubit in self.coupled_qubits
            },
            "cz_pulse_frequencies_sweep": {
                qubit: np.linspace(-20e6, 20e6, 21) + self.ac_freq
                for qubit in self.coupled_qubits
            },
        }
        self.validate()

    def validate(self) -> None:
        all_coupled_qubits = []
        for coupler in self.couplers:
            all_coupled_qubits += coupler.split("_")
        if len(all_coupled_qubits) > len(set(all_coupled_qubits)):
            print("Couplers share qubits")
            raise ValueError("Improper Couplers")

    def transition_frequency(self, coupler: str):
        coupled_qubits = coupler.split(sep="_")
        q1_f01 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[0]}", "freq_01")
        )
        q2_f01 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[1]}", "freq_01")
        )
        q1_f12 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[0]}", "freq_12")
        )
        q2_f12 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[1]}", "freq_12")
        )
        # ac_freq = np.abs(q1_f01 + q2_f01 - (q1_f01 + q1_f12))
        ac_freq = np.min(
            [
                np.abs(q1_f01 + q2_f01 - (q1_f01 + q1_f12)),
                np.abs(q1_f01 + q2_f01 - (q2_f01 + q2_f12)),
            ]
        )
        ac_freq = int(ac_freq / 1e4) * 1e4
        print(f"{ ac_freq/1e6 = } MHz for coupler: {coupler}")
        return ac_freq


class CZ_Chevron_Amplitude_Node(BaseNode):
    measurement_obj = CZ_chevron_amplitude
    analysis_obj = CZChevronAmplitudeAnalysis

    def __init__(
        self, name: str, all_qubits: list[str], couplers: list[str], **node_dictionary
    ):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.all_qubits = all_qubits
        self.couplers = couplers
        self.edges = couplers
        self.coupler = self.couplers[0]
        self.redis_field = ["cz_pulse_frequency", "cz_pulse_amplitude"]
        self.qubit_state = 0
        self.all_qubits = [q for bus in couplers for q in bus.split("_")]
        self.coupler_samplespace = self.samplespace
        self.node_dictionary["cz_pulse_duration"] = 128e-9
        REDIS_CONNECTION.hset(
            f"couplers:{self.coupler}",
            "cz_pulse_duration",
            self.node_dictionary["cz_pulse_duration"] * 2,
        )
        self.schedule_samplespace = {
            "cz_pulse_amplitudes": {
                coupler: np.linspace(0.05, 0.3, 15) for coupler in self.couplers
            },
            "cz_pulse_frequencies": {
                coupler: np.linspace(-10e6, 6e6, 15)
                + self.transition_frequency(coupler)
                for coupler in self.couplers
            },
        }
        self.validate()

    def validate(self) -> None:
        all_coupled_qubits = []
        for coupler in self.couplers:
            all_coupled_qubits += coupler.split("_")
        if len(all_coupled_qubits) > len(set(all_coupled_qubits)):
            print("Couplers share qubits")
            raise ValueError("Improper Couplers")

    def transition_frequency(self, coupler: str):
        coupled_qubits = coupler.split(sep="_")
        q1_f01 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[0]}", "clock_freqs:f01")
        )
        q2_f01 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[1]}", "clock_freqs:f01")
        )
        q1_f12 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[0]}", "clock_freqs:f12")
        )
        q2_f12 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[1]}", "clock_freqs:f12")
        )
        # ac_freq = np.abs(q1_f01 + q2_f01 - (q1_f01 + q1_f12))
        ac_freq = np.max(
            [
                np.abs(q1_f01 + q2_f01 - (q1_f01 + q1_f12)),
                np.abs(q1_f01 + q2_f01 - (q2_f01 + q2_f12)),
            ]
        )
        ac_freq = int(ac_freq / 1e4) * 1e4
        # lo = 4.4e9 - (ac_freq - 450e6)
        # print(f'{ ac_freq/1e6 = } MHz for coupler: {coupler}')
        # print(f'{ lo/1e9 = } GHz for coupler: {coupler}')
        return ac_freq


class CZ_Optimize_Chevron_Node(BaseNode):
    measurement_obj = CZ_chevron
    analysis_obj = CZChevronAnalysis

    def __init__(self, name: str, all_qubits: list[str], couplers: list[str]):
        super().__init__(name, all_qubits)
        self.type = "optimized_sweep"
        self.couplers = couplers
        self.coupler = self.couplers[0]
        self.redis_field = ["cz_pulse_frequency", "cz_pulse_duration"]
        self.optimization_field = "cz_pulse_duration"
        self.qubit_state = 0
        self.all_qubits = [q for bus in couplers for q in bus.split("_")]
        self.schedule_samplespace = {
            "cz_pulse_durations": {
                coupler: np.arange(100e-9, 1000e-9, 320e-9) for coupler in self.couplers
            },
            "cz_pulse_frequencies": {
                coupler: np.linspace(-2.0e6, 2.0e6, 5)
                + self.transition_frequency(coupler)
                for coupler in self.couplers
            },
        }
        self.coupler_samplespace = self.schedule_samplespace
        self.validate()

    def validate(self) -> None:
        all_coupled_qubits = []
        for coupler in self.couplers:
            all_coupled_qubits += coupler.split("_")
        if len(all_coupled_qubits) > len(set(all_coupled_qubits)):
            print("Couplers share qubits")
            raise ValueError("Improper Couplers")

    def transition_frequency(self, coupler: str):
        coupled_qubits = coupler.split(sep="_")
        q1_f01 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[0]}", "freq_01")
        )
        q2_f01 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[1]}", "freq_01")
        )
        q1_f12 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[0]}", "freq_12")
        )
        q2_f12 = float(
            REDIS_CONNECTION.hget(f"transmons:{coupled_qubits[1]}", "freq_12")
        )
        # ac_freq = np.abs(q1_f01 + q2_f01 - (q1_f01 + q1_f12))
        ac_freq = np.max(
            [
                np.abs(q1_f01 + q2_f01 - (q1_f01 + q1_f12)),
                np.abs(q1_f01 + q2_f01 - (q2_f01 + q2_f12)),
            ]
        )
        ac_freq = int(ac_freq / 1e4) * 1e4
        print(f"{ ac_freq/1e6 = } MHz for coupler: {coupler}")
        return ac_freq


class Reset_Chevron_Node(BaseNode):
    # TODO: Replaced Reset_CZ_Chevron with Reset_calibration_SSRO, is that correct?
    measurement_obj = Reset_calibration_SSRO
    analysis_obj = CZChevronAnalysisReset

    def __init__(
        self, name: str, all_qubits: list[str], couplers: list[str], **node_dictionary
    ):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.all_qubits = all_qubits
        self.couplers = couplers
        self.edges = couplers
        self.coupler = self.couplers[0]
        self.redis_field = ["reset_amplitude_qc", "reset_duration_qc"]
        self.qubit_state = 0
        self.coupled_qubits = self.couplers[0].split(sep="_")
        self.schedule_samplespace = {
            "cz_pulse_durations": {  # g
                qubit: np.linspace(0.001, 0.1, 26) for qubit in self.coupled_qubits
            },
            "cz_pulse_amplitudes": {  # ft
                qubit: np.linspace(0, -0.4, 26) for qubit in self.coupled_qubits
            },
        }
        # self.node_dictionary['duration_offset'] = 0
        # print(f'{ self.coupled_qubits = }')

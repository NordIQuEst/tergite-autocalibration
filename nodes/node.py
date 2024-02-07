import numpy as np
import redis
from calibration_schedules.resonator_spectroscopy import Resonator_Spectroscopy
from calibration_schedules.two_tones_spectroscopy import Two_Tones_Spectroscopy
# from calibration_schedules.two_tone_multidim import Two_Tones_Multidim
from calibration_schedules.two_tone_multidim_loop_reversed import Two_Tones_Multidim
from calibration_schedules.rabi_oscillations import Rabi_Oscillations
from calibration_schedules.T1 import T1,T2, T2Echo
from calibration_schedules.XY_crosstalk import XY_cross
from calibration_schedules.punchout import Punchout
from calibration_schedules.ramsey_fringes import Ramsey_fringes
from calibration_schedules.ro_frequency_optimization import RO_frequency_optimization
from calibration_schedules.ro_amplitude_optimization import RO_amplitude_optimization
from calibration_schedules.state_discrimination import Single_Shots_RO
from calibration_schedules.motzoi_parameter import Motzoi_parameter
from calibration_schedules.n_rabi_oscillations import N_Rabi_Oscillations
from calibration_schedules.randomized_benchmarking import Randomized_Benchmarking
from calibration_schedules.check_cliffords import Check_Cliffords
from nodes.base_node import Base_Node



# from calibration_schedules.cz_chevron import CZ_chevron
# from calibration_schedules.cz_chevron_reversed import CZ_chevron, Reset_chevron_dc
from calibration_schedules.cz_chevron_reversed import CZ_chevron
# from calibration_schedules.cz_calibration import CZ_calibration, CZ_calibration_SSRO,CZ_dynamic_phase

from analysis.motzoi_analysis import MotzoiAnalysis
from analysis.resonator_spectroscopy_analysis import (
    ResonatorSpectroscopyAnalysis,
    ResonatorSpectroscopy_1_Analysis,
    ResonatorSpectroscopy_2_Analysis
)
from analysis.qubit_spectroscopy_analysis import QubitSpectroscopyAnalysis
from analysis.qubit_spectroscopy_multidim import QubitSpectroscopyMultidim
from analysis.optimum_ro_frequency_analysis import (
    OptimalROFrequencyAnalysis,
    OptimalRO_012_FrequencyAnalysis
)
from analysis.optimum_ro_amplitude_analysis import OptimalROAmplitudeAnalysis
from analysis.state_discrimination_analysis import StateDiscrimination
from analysis.rabi_analysis import RabiAnalysis
from analysis.punchout_analysis import PunchoutAnalysis
from analysis.ramsey_analysis import RamseyAnalysis
from analysis.tof_analysis import analyze_tof
from analysis.T1_analysis import T1Analysis, T2Analysis, T2EchoAnalysis
# from analysis.cz_chevron_analysis import CZChevronAnalysis, CZChevronAnalysisReset
# from analysis.cz_calibration_analysis import CZCalibrationAnalysis, CZCalibrationSSROAnalysis
from analysis.n_rabi_analysis import NRabiAnalysis
from analysis.randomized_benchmarking_analysis import RandomizedBenchmarkingAnalysis
from analysis.check_cliffords_analysis import CheckCliffordsAnalysis


from config_files.VNA_LOKIB_values import (
    VNA_resonator_frequencies, VNA_qubit_frequencies, VNA_f12_frequencies
)
from nodes.coupler_nodes import (
    CZ_Optimize_Chevron_Node, Coupler_Resonator_Spectroscopy_Node, Coupler_Spectroscopy_Node, CZ_Chevron_Node
)

redis_connection = redis.Redis(decode_responses=True)

def resonator_samples(qubit: str) -> np.ndarray:
    res_spec_samples = 101
    sweep_range =  2.0e6
    VNA_frequency = VNA_resonator_frequencies[qubit]
    min_freq = VNA_frequency - sweep_range / 2 -0.5e6
    max_freq = VNA_frequency + sweep_range / 2
    return np.linspace(min_freq, max_freq, res_spec_samples)


def qubit_samples(qubit: str, transition: str = '01') -> np.ndarray:
    qub_spec_samples = 41
    sweep_range = 3.0e6
    if transition == '01':
        VNA_frequency = VNA_qubit_frequencies[qubit]
    elif transition == '12':
        VNA_frequency = VNA_f12_frequencies[qubit]
    else:
        VNA_frequency = VNA_value
    min_freq = VNA_frequency - sweep_range / 2
    max_freq = VNA_frequency + sweep_range / 2
    return np.linspace(min_freq, max_freq, qub_spec_samples)


class NodeFactory:
    def __init__(self):
        self.node_implementations = {
            'punchout': Punchout_Node,
            'resonator_spectroscopy': Resonator_Spectroscopy_Node,
            'qubit_01_spectroscopy_pulsed': Qubit_01_Spectroscopy_Pulsed_Node,
            'qubit_01_spectroscopy_multidim': Qubit_01_Spectroscopy_Multidim_Node,
            'rabi_oscillations': Rabi_Oscillations_Node,
            'ramsey_correction': Ramsey_Fringes_Node,
            'resonator_spectroscopy_1': Resonator_Spectroscopy_1_Node,
            'qubit_12_spectroscopy_pulsed': Qubit_12_Spectroscopy_Pulsed_Node,
            'qubit_12_spectroscopy_multidim': Qubit_12_Spectroscopy_Multidim_Node,
            'rabi_oscillations_12': Rabi_Oscillations_12_Node,
            'ramsey_correction_12': Ramsey_Fringes_12_Node,
            'resonator_spectroscopy_2': Resonator_Spectroscopy_2_Node,
            'motzoi_parameter': Motzoi_Parameter_Node,
            'n_rabi_oscillations': N_Rabi_Oscillations_Node,
            'coupler_spectroscopy': Coupler_Spectroscopy_Node,
            'coupler_resonator_spectroscopy': Coupler_Resonator_Spectroscopy_Node,
            'T1': T1_Node,
            'T2': T2_Node,
            'T2_echo': T2_Echo_Node,
            'reset_chevron': Reset_Chevron_Node,
            'cz_chevron': CZ_Chevron_Node,
            'cz_optimize_chevron': CZ_Optimize_Chevron_Node,
            'cz_calibration': CZ_Calibration_Node,
            'cz_calibration_ssro': CZ_Calibration_SSRO_Node,
            'cz_dynamic_phase': CZ_Dynamic_Phase_Node,
            'ro_frequency_optimization': RO_frequency_optimization_Node,
            'ro_frequency_optimization_gef': RO_frequency_optimization_gef_Node,
            'ro_amplitude_optimization_gef': RO_amplitude_optimization_gef_Node,
            #'ro_frequency_optimization_gef': RO_frequency_optimization_gef_Node,
            'randomized_benchmarking': Randomized_Benchmarking_Node,
            'check_cliffords': Check_Cliffords_Node,
        }
    def all_nodes(self):
        return list(self.node_implementations.keys())

    def create_node(self, node_name: str, all_qubits: list[str], ** kwargs):
        node_object = self.node_implementations[node_name](node_name, all_qubits, ** kwargs)
        return node_object




class Resonator_Spectroscopy_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['ro_freq', 'Ql', 'resonator_minimum']
        self.qubit_state = 0
        self.measurement_obj = Resonator_Spectroscopy
        self.analysis_obj = ResonatorSpectroscopyAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ro_frequencies': {
                qubit: resonator_samples(qubit) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace

class Punchout_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['ro_ampl']
        self.qubit_state = 0
        self.measurement_obj = Punchout
        self.analysis_obj = PunchoutAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ro_frequencies': {
                qubit: resonator_samples(qubit) for qubit in self.all_qubits
            },
            'ro_amplitudes': {
                qubit: np.linspace(0.005, 0.022, 8) for qubit in self.all_qubits
            },
        }
        return cluster_samplespace

class Qubit_01_Spectroscopy_Pulsed_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.sweep_range = self.node_dictionary.pop("sweep_range", None)
        self.redis_field = ['freq_01']
        self.qubit_state = 0
        self.measurement_obj = Two_Tones_Spectroscopy
        self.analysis_obj = QubitSpectroscopyAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'spec_frequencies': {
                qubit: qubit_samples(qubit, sweep_range=self.sweep_range) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace

class Qubit_01_Spectroscopy_Multidim_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['freq_01',
                            'spec_ampl_optimal']
        self.qubit_state = 0
        self.measurement_obj = Two_Tones_Multidim
        self.analysis_obj = QubitSpectroscopyMultidim

    @property
    def samplespace(self):
        cluster_samplespace = {
            'spec_pulse_amplitudes': {
                 qubit: np.linspace(3e-4, 9e-4, 5) for qubit in self.all_qubits
            },
            'spec_frequencies': {
                qubit: qubit_samples(qubit) for qubit in self.all_qubits
            },
        }
        return cluster_samplespace

class Rabi_Oscillations_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['mw_amp180']
        self.qubit_state = 0
        self.measurement_obj = Rabi_Oscillations
        self.analysis_obj = RabiAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'mw_amplitudes': {
                qubit: np.linspace(0.002, 0.80, 101) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace


class Ramsey_Fringes_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['freq_01']
        self.qubit_state = 0
        self.measurement_obj = Ramsey_fringes
        self.analysis_obj = RamseyAnalysis
        self.backup = False
        self.analysis_kwargs = {"redis_field":"freq_01"}

    @property
    def samplespace(self):
        cluster_samplespace = {
            # 'ramsey_fringes': {
                'ramsey_delays': {
                    qubit: np.arange(4e-9, 2048e-9, 8 * 8e-9) for qubit in self.all_qubits
                },
                'artificial_detunings': {
                    qubit: np.arange(-2.1, 2.1, 0.8) * 1e6 for qubit in self.all_qubits
                },
            # },
        }
        return cluster_samplespace


class Ramsey_Fringes_12_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['freq_12']
        self.qubit_state = 1
        self.measurement_obj = Ramsey_fringes
        self.analysis_obj = RamseyAnalysis
        self.backup = False
        self.analysis_kwargs = {"redis_field":"freq_12"}

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ramsey_delays': {
                qubit: np.arange(4e-9, 2048e-9, 8 * 8e-9) for qubit in self.all_qubits
            },
            'artificial_detunings': {
                qubit: np.arange(-2.1, 2.1, 0.8) * 1e6 for qubit in self.all_qubits
            },
        }
        return cluster_samplespace

class Motzoi_Parameter_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['mw_motzoi']
        self.qubit_state = 0
        self.measurement_obj = Motzoi_parameter
        self.analysis_obj = MotzoiAnalysis
        self.backup = False

    @property
    def samplespace(self):
        cluster_samplespace = {
            'mw_motzois': {qubit: np.linspace(-0.5,0.5,61) for qubit in self.all_qubits},
            'X_repetitions': {qubit : np.arange(2, 17, 4) for qubit in self.all_qubits}
        }
        return cluster_samplespace

class N_Rabi_Oscillations_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['mw_amp180']
        self.qubit_state = 0
        self.measurement_obj = N_Rabi_Oscillations
        self.analysis_obj = NRabiAnalysis
        self.backup = False

    @property
    def samplespace(self):
        cluster_samplespace = {
            'mw_amplitudes_sweep': {qubit: np.linspace(-0.1,0.1,61) for qubit in self.all_qubits},
            'X_repetitions': {qubit : np.arange(1, 16, 4) for qubit in self.all_qubits}
        }
        return cluster_samplespace

class T1_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['t1_time']
        self.qubit_state = 0
        self.measurement_obj = T1
        self.analysis_obj = T1Analysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'delays': {qubit : 8e-9 +  np.arange(0,300e-6,6e-6) for qubit in self.all_qubits}
        }
        return cluster_samplespace

class Randomized_Benchmarking_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.all_qubits = all_qubits
        self.node_dictionary = node_dictionary
        self.backup = False
        self.redis_field = ['t1_time'] #TODO change to something, error?
        self.qubit_state = 0 #can be 0 or 1
        self.measurement_obj = Randomized_Benchmarking
        self.analysis_obj = RandomizedBenchmarkingAnalysis

    @property
    def samplespace(self):
        numbers = 2 ** np.arange(1,12,3)
        extra_numbers = [numbers[i] + numbers[i+1] for i in range(len(numbers)-2)]
        extra_numbers = np.array(extra_numbers)
        calibration_points = np.array([0,1])
        all_numbers = np.sort( np.concatenate((numbers, extra_numbers)) )
        # all_numbers = numbers

        all_numbers =  np.concatenate((all_numbers, calibration_points))

        number_of_repetitions = 1

        cluster_samplespace = {
            'number_of_cliffords': {
                # qubit: all_numbers for qubit in self.all_qubits
                qubit: np.array([2, 16, 128, 256,512, 768, 1024, 0, 1]) for qubit in self.all_qubits
            },
            'sequence_repetitions': {
                qubit: np.ones(number_of_repetitions) for qubit in self.all_qubits
            },
        }
        return cluster_samplespace

class Check_Cliffords_Node:
    def __init__(self, name: str, all_qubits: list[str], ** kwargs):
        self.name = name
        self.all_qubits = all_qubits
        self.node_dictionary = kwargs
        self.redis_field = ['t1_time'] #TODO Empty?
        self.qubit_state = 0
        self.measurement_obj = Check_Cliffords
        self.analysis_obj = CheckCliffordsAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'clifford_indices': {
                qubit: np.linspace(0,25) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace


class T2_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.redis_field = ['t2_time']
        self.qubit_state = 0
        self.measurement_obj = T2
        self.analysis_obj = T2Analysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'delays': {qubit : 8e-9 + np.arange(0,100e-6,1e-6) for qubit in self.all_qubits}
        }
        return cluster_samplespace

class T2_Echo_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.redis_field = ['t2_time']
        self.qubit_state = 0
        self.measurement_obj = T2Echo
        self.analysis_obj = T2EchoAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'delays': {qubit : 8e-9 + np.arange(0,300e-6,6e-6) for qubit in self.all_qubits}
        }
        return cluster_samplespace

class Resonator_Spectroscopy_1_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['ro_freq_1', 'Ql_1', 'resonator_minimum_1']
        self.qubit_state = 1
        self.measurement_obj = Resonator_Spectroscopy
        self.analysis_obj = ResonatorSpectroscopy_1_Analysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ro_frequencies': {
                qubit: resonator_samples(qubit) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace


class Resonator_Spectroscopy_2_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['ro_freq_2']
        self.qubit_state = 2
        self.measurement_obj = Resonator_Spectroscopy
        self.analysis_obj = ResonatorSpectroscopy_2_Analysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ro_frequencies': {
                qubit: resonator_samples(qubit) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace


class Qubit_12_Spectroscopy_Pulsed_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.sweep_range = self.node_dictionary.pop("sweep_range", None)
        self.redis_field = ['freq_12']
        self.qubit_state = 1
        self.measurement_obj = Two_Tones_Spectroscopy
        self.analysis_obj = QubitSpectroscopyAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'spec_frequencies': {
                qubit: qubit_samples(qubit, '12', sweep_range=self.sweep_range) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace


class Qubit_12_Spectroscopy_Multidim_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['freq_12',
                            'spec_ampl_12_optimal']
        self.qubit_state = 1
        self.measurement_obj = Two_Tones_Multidim
        self.analysis_obj = QubitSpectroscopyMultidim

    @property
    def samplespace(self):
        cluster_samplespace = {
            'spec_pulse_amplitudes': {
                 qubit: np.linspace(5e-4, 9e-4, 5) for qubit in self.all_qubits
            },
            'spec_frequencies': {
                qubit: qubit_samples(qubit, transition='12') for qubit in self.all_qubits
            },
        }
        return cluster_samplespace

class Rabi_Oscillations_12_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, ** node_dictionary)
        self.redis_field = ['mw_ef_amp180']
        self.qubit_state = 1
        self.measurement_obj = Rabi_Oscillations
        self.analysis_obj = RabiAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'mw_amplitudes': {
                qubit: np.linspace(0.002, 0.400, 31) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace


class RO_frequency_optimization_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.redis_field = ['ro_freq_opt']
        self.qubit_state = 0
        self.measurement_obj = RO_frequency_optimization
        self.analysis_obj = OptimalROFrequencyAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ro_opt_frequencies': {
                qubit: resonator_samples(qubit) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace

class RO_frequency_optimization_gef_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.all_qubits = all_qubits
        self.redis_field = ['ro_freq_opt']
        self.qubit_state = 2
        self.measurement_obj = RO_frequency_optimization
        self.analysis_obj = OptimalRO_012_FrequencyAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ro_opt_frequencies': {
                qubit: resonator_samples(qubit) for qubit in self.all_qubits
            }
        }
        return cluster_samplespace

class RO_amplitude_optimization_gef_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.all_qubits = all_qubits
        self.redis_field = ['ro_ampl_opt','inv_cm_opt']
        self.qubit_state = 2
        self.measurement_obj = RO_amplitude_optimization
        self.analysis_obj = OptimalROAmplitudeAnalysis

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ro_amplitudes': {qubit : np.linspace(0.001,0.121,31) for qubit in self.all_qubits}
        }
        return cluster_samplespace


class Reset_Chevron_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], couplers: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.all_qubits = all_qubits
        self.all_couplers = couplers
        self.coupler = couplers[0]
        self.redis_field = ['reset_amplitude_qc','reset_duration_qc']
        self.qubit_state = 0
        self.measurement_obj = Reset_chevron_dc
        self.analysis_obj = CZChevronAnalysisReset
        self.coupled_qubits = couplers[0].split(sep='_')
        # print(f'{ self.coupled_qubits = }')

    @property
    def samplespace(self):
        # print(f'{ np.linspace(- 50e6, 50e6, 2) + self.ac_freq = }')
        cluster_samplespace = {
            # Pulse test
            'cz_pulse_durations': {
                qubit: 4e-9+np.linspace(16e-9, 16e-9, 11)  for qubit in self.coupled_qubits
            },
            'cz_pulse_amplitudes': {
                qubit: np.linspace(0.4, 0.4, 11) for qubit in self.coupled_qubits
            },

            # For DC reset
            # 'cz_pulse_durations': {
            #     qubit: 4e-9+np.arange(0e-9, 12*4e-9,4e-9) for qubit in self.coupled_qubits
            # },
            # 'cz_pulse_amplitudes': {
            #     qubit: np.linspace(0.2, 0.8, 61) for qubit in self.coupled_qubits
            # },

            # For AC reset
            # 'cz_pulse_durations': {
            #     qubit: 4e-9+np.arange(0e-9, 36*100e-9,400e-9) for qubit in self.coupled_qubits
            # },
            # 'cz_pulse_frequencies_sweep': {
            #     qubit: np.linspace(210e6, 500e6, 51) + self.ac_freq for qubit in self.coupled_qubits
            # },
        }
        return cluster_samplespace


class CZ_Calibration_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], couplers: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.coupler = couplers[0]
        # print(couplers)
        self.coupled_qubits = couplers[0].split(sep='_')
        # print(self.coupled_qubits)
        # self.node_dictionary = kwargs
        self.redis_field = ['cz_phase','cz_pop_loss']
        self.qubit_state = 2
        self.testing_group = 0 # The edge group to be tested. 0 means all edges.
        self.dynamic = False
        self.measurement_obj = CZ_calibration
        self.analysis_obj = CZCalibrationAnalysis
        # self.validate()

    @property
    def samplespace(self):
        cluster_samplespace = {
            'ramsey_phases': {qubit: np.linspace(0, 360, 31) for qubit in  self.coupled_qubits},
            'control_ons': {qubit: [False,True] for qubit in  self.coupled_qubits},
        }
        return cluster_samplespace

class CZ_Calibration_SSRO_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], couplers: list[str], ** node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.coupler = couplers[0]
        self.coupled_qubits = couplers[0].split(sep='_')
        # self.node_dictionary = kwargs
        self.redis_field = ['cz_phase','cz_pop_loss','cz_leakage']
        self.qubit_state = 2
        self.testing_group = 0 # The edge group to be tested. 0 means all edges.
        self.dynamic = False
        self.measurement_obj = CZ_calibration_SSRO
        self.analysis_obj = CZCalibrationSSROAnalysis
        # self.validate()

    @property
    def samplespace(self):
        cluster_samplespace = {
            'control_ons': {qubit: [False,True] for qubit in  self.coupled_qubits},
            'ramsey_phases': {qubit: np.linspace(0, 360, 13) for qubit in  self.coupled_qubits},
            # 'ramsey_phases': {qubit: np.linspace(0.025, 0.025, 1) for qubit in  self.coupled_qubits},
        }
        return cluster_samplespace

class CZ_Dynamic_Phase_Node(Base_Node):
    def __init__(self, name: str, all_qubits: list[str], couplers: list[str], ** kwargs):
        self.name = name
        self.all_qubits = all_qubits
        self.all_couplers = couplers
        self.node_dictionary = kwargs
        self.coupler = couplers[0]
        # print(couplers)
        self.coupled_qubits = couplers[0].split(sep='_')
        # print(self.coupled_qubits)
        # self.node_dictionary = kwargs
        self.redis_field = ['cz_phase']
        self.qubit_state = 2
        self.testing_group = 0 # The edge group to be tested. 0 means all edges.
        self.dynamic = True
        self.measurement_obj = CZ_dynamic_phase
        self.analysis_obj = CZCalibrationAnalysis

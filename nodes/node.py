import networkx as nx
import numpy as np
from calibration_schedules.resonator_spectroscopy import Resonator_Spectroscopy
from calibration_schedules.two_tones_spectroscopy import Two_Tones_Spectroscopy
from calibration_schedules.two_tone_multidim import Two_Tones_Multidim
from calibration_schedules.rabi_oscillations import Rabi_Oscillations
from calibration_schedules.T1 import T1_BATCHED
from calibration_schedules.XY_crosstalk import XY_cross
from calibration_schedules.punchout import Punchout
from calibration_schedules.ramsey_fringes import Ramsey_fringes
from calibration_schedules.ro_frequency_optimization import RO_frequency_optimization
from calibration_schedules.ro_amplitude_optimization import RO_amplitude_optimization
from calibration_schedules.state_discrimination import Single_Shots_RO
# from calibration_schedules.drag_amplitude import DRAG_amplitude
from calibration_schedules.motzoi_parameter import Motzoi_parameter
from analysis.motzoi_analysis import MotzoiAnalysis
from analysis.resonator_spectroscopy_analysis import (
    ResonatorSpectroscopyAnalysis,
    ResonatorSpectroscopy_1_Analysis,
    ResonatorSpectroscopy_2_Analysis
)
from analysis.qubit_spectroscopy_analysis import QubitSpectroscopyAnalysis
from analysis.qubit_spectroscopy_multidim import QubitSpectroscopyMultidim
from analysis.coupler_spectroscopy_analysis import CouplerSpectroscopyAnalysis
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
from analysis.T1_analysis import T1Analysis

from config_files.VNA_values import (
    VNA_resonator_frequencies, VNA_qubit_frequencies, VNA_f12_frequencies
)


graph = nx.DiGraph()

# dependencies: n1 -> n2. For example
# ('tof','resonator_spectroscopy')
# means 'resonator_spectroscopy' depends on 'tof'
graph_dependencies = [
    ('tof', 'resonator_spectroscopy'),
    ('resonator_spectroscopy', 'coupler_spectroscopy'),
    ('resonator_spectroscopy', 'qubit_01_spectroscopy_pulsed'),
    ('resonator_spectroscopy', 'qubit_01_spectroscopy_multidim'),
    ('qubit_01_spectroscopy_pulsed', 'rabi_oscillations'),
    ('qubit_01_spectroscopy_multidim', 'rabi_oscillations'),
    ('rabi_oscillations', 'ramsey_correction'),
    ('ramsey_correction', 'resonator_spectroscopy_1'),
    ('ramsey_correction', 'ro_frequency_optimization'),
    ('ro_frequency_optimization', 'ro_amplitude_optimization'),
    ('ro_amplitude_optimization', 'state_discrimination'),
    ('ramsey_correction', 'T1'),
    ('resonator_spectroscopy_1', 'qubit_12_spectroscopy_pulsed'),
    ('qubit_12_spectroscopy_pulsed', 'rabi_oscillations_12'),
    ('rabi_oscillations_12', 'ramsey_correction_12'),
]

graph.add_edges_from(graph_dependencies)
# For DEVELOPMENT PURPOSES the nodes that update an existing redis redis_field
# are given a refine attr so they can be skipped if desired
graph.add_node('tof', type='refine')
graph.add_node('punchout')
graph.add_node('qubit_01_spectroscopy_pulsed')
graph.add_node('qubit_01_spectroscopy_multidim')
graph.add_node('ramsey_correction', type='refine')
graph.add_node('ramsey_correction_12', type='refine')
graph.add_node('ro_frequency_optimization', type='refine')
graph.add_node('ro_amplitude_optimization', type='refine')

# some nodes target exactly the same redis field. Assign a weight to sort them
graph['resonator_spectroscopy']['qubit_01_spectroscopy_pulsed']['weight'] = 1
graph['resonator_spectroscopy']['qubit_01_spectroscopy_multidim']['weight'] = 2

all_nodes = list(nx.topological_sort(graph))


def filtered_topological_order(target_node: str):
    if target_node == 'punchout':
        topo_order = ['punchout']
    else:
        topo_order = nx.shortest_path(
            graph, 'resonator_spectroscopy', target_node, weight='weight'
        )

    def graph_condition(node, types):
        is_without_type = 'type' not in graph.nodes[node]
        if is_without_type:
            return True
        has_correct_type = graph.nodes[node]['type'] in types
        return not is_without_type and has_correct_type

    filtered_order = [node for node in topo_order if graph_condition(node, 'none')]
    return filtered_order


def resonator_samples(qubit: str) -> np.ndarray:
    res_spec_samples = 55
    sweep_range = 5.5e6
    VNA_frequency = VNA_resonator_frequencies[qubit]
    min_freq = VNA_frequency - sweep_range / 2
    max_freq = VNA_frequency + sweep_range / 2
    return np.linspace(min_freq, max_freq, res_spec_samples)


def qubit_samples(qubit: str, transition: str = '01') -> np.ndarray:
    qub_spec_samples = 45
    sweep_range = 3.5e6
    if transition == '01':
        VNA_frequency = VNA_qubit_frequencies[qubit]
    elif transition == '12':
        VNA_frequency = VNA_f12_frequencies[qubit]
    else:
        raise ValueError('Invalid transition')

    min_freq = VNA_frequency - sweep_range / 2
    max_freq = VNA_frequency + sweep_range / 2
    return np.linspace(min_freq, max_freq, qub_spec_samples)


class Node():
    def __init__(self, name: str, all_qubits: list[str], ** kwargs):
        self.name = name
        self.all_qubits = all_qubits
        self.node_dictionary = kwargs
        self.initialize_node(self.name)

        def initialize_node(name: str):
            initial_parameters = node_definitions[self.name]
            self.redis_field = initial_parameters['redis_field']
            self.qubit_state = initial_parameters['qubit_state']  # e.g. qubit_state = 1 for resonator_spectroscopy_1
            self.measurement_obj = initial_parameters['measurement_obj']
            self.analysis_obj = initial_parameters['analysis_obj']
            self.default_sample_array = initial_parameters['default_sample_array']

        @property
        def spi_samplespace(self):
            _spi_samplespace = {self.name: {}}
            coupled_qubits = self.node_dictionary['coupled_qubits']
            self.coupler = coupled_qubits[0] + coupled_qubits[1]
            if self.name in ['coupler_spectroscopy']:
                _spi_samplespace[self.name] = {
                    'dc_currents': {self.coupler: np.arange(-3e-3, 3e-3, 100e6)},
                }

        @property
        def samplespace(self):
            _samplespace = {self.name: {}}
            if self.name in ['coupler_spectroscopy']:
                if 'coupled_qubits' in self.node_dictionary:
                    coupled_qubits = self.node_dictionary['coupled_qubits']
                    self.coupler = coupled_qubits[0] + coupled_qubits[1]
                    _samplespace[self.name] = {
                        'spec_frequencies': {
                            qubit: qubit_samples(qubit) for qubit in coupled_qubits
                        },
                    }
                else:
                    raise ValueError('User dictionary must contain an "coupled_qubits" field')
            elif self.name in [
                    'resonator_spectroscopy',
                    'resonator_spectroscopy_1',
                    'resonator_spectroscopy_2',
            ]:
                _samplespace[self.name] = {
                    'ro_frequencies': {
                        qubit: resonator_samples(qubit) for qubit in self.all_qubits
                    }
                }
            elif self.name == 'qubit_01_spectroscopy_pulsed':
                _samplespace[self.name] = {
                    'spec_frequencies': {
                        qubit: qubit_samples(qubit) for qubit in self.all_qubits
                    }
                }
            elif self.name == 'qubit_12_spectroscopy_pulsed':
                _samplespace[self.name] = {
                    'spec_frequencies': {
                        qubit: qubit_samples(qubit, '12') for qubit in self.all_qubits
                    }
                }
            elif self.name in ['rabi_oscillations', 'rabi_oscillations_12']:
                _samplespace[self.name] = {
                    'mw_amplitudes': {
                        qubit: np.linspace(0.002, 0.200, 31) for qubit in self.all_qubits
                    }
                }
            elif self.name == 'ramsey_correction':
                _samplespace[self.name] = {
                    'ramsey_correction': {
                        'ramsey_delays': {qubit: np.arange(4e-9, 2048e-9, 8 * 8e-9) for qubit in self.all_qubits},
                        'artificial_detunings': {qubit: np.arange(-2.1, 2.1, 0.8) * 1e6 for qubit in self.all_qubits},
                    },
                }
            elif self.name == 'ramsey_correction_12':
                _samplespace[self.name] = {
                    'ramsey_correction': {
                        'ramsey_delays': {qubit: np.arange(4e-9, 2048e-9, 8 * 8e-9) for qubit in self.all_qubits},
                        'artificial_detunings': {qubit: np.arange(-2.1, 2.1, 0.8) * 1e6 for qubit in self.all_qubits},
                    },
                }


node_definitions = {
    'resonator_spectroscopy': {
        'redis_field': 'ro_freq',
        'qubit_state': 0,
        'measurement_obj': Resonator_Spectroscopy,
        'analysis_obj': ResonatorSpectroscopyAnalysis
    },
    'qubit_01_spectroscopy_pulsed': {
        'redis_field': 'freq_01',
        'qubit_state': 0,
        'measurement_obj': Two_Tones_Spectroscopy,
        'analysis_obj': QubitSpectroscopyAnalysis
    },
    'rabi_oscillations': {
        'redis_field': 'mw_amp180',
        'qubit_state': 0,
        'measurement_obj': Rabi_Oscillations,
        'analysis_obj': RabiAnalysis
    },
    'ramsey_correction': {
        'redis_field': 'freq_01',
        'qubit_state': 0,
        'measurement_obj': Ramsey_fringes,
        'analysis_obj': RamseyAnalysis
    },
    'motzoi_parameter': {
        'redis_field': 'mw_motzoi',
        'qubit_state': 0,
        'measurement_obj': Motzoi_parameter,
        'analysis_obj': MotzoiAnalysis
    },
    'resonator_spectroscopy_1': {
        'redis_field': 'ro_freq_1',
        'qubit_state': 1,
        'measurement_obj': Resonator_Spectroscopy,
        'analysis_obj': ResonatorSpectroscopy_1_Analysis
    },
    'T1': {
        'redis_field': 't1_time',
        'qubit_state': 0,
        'measurement_obj': T1_BATCHED,
        'analysis_obj': T1Analysis
    },
    'two_tone_multidim': {
        'redis_field': 'freq_01',
        'qubit_state': 0,
        'measurement_obj': Two_Tones_Multidim,
        'analysis_obj': QubitSpectroscopyMultidim
    },
    'qubit_12_spectroscopy_pulsed': {
        'redis_field': 'freq_12',
        'qubit_state': 1,
        'measurement_obj': Two_Tones_Spectroscopy,
        'analysis_obj': QubitSpectroscopyAnalysis
    },
    'rabi_oscillations_12': {
        'redis_field': 'mw_ef_amp180',
        'qubit_state': 1,
        'measurement_obj': Rabi_Oscillations,
        'analysis_obj': RabiAnalysis
    },
    'ramsey_correction_12': {
        'redis_field': 'freq_12',
        'qubit_state': 1,
        'measurement_obj': Ramsey_fringes,
        'analysis_obj': RamseyAnalysis
    },
    'resonator_spectroscopy_2': {
        'redis_field': 'ro_freq_2',
        'qubit_state': 2,
        'measurement_obj': Resonator_Spectroscopy,
        'analysis_obj': ResonatorSpectroscopy_2_Analysis
    },
    'punchout': {
        'redis_field': 'ro_amp',
        'qubit_state': 0,
        'measurement_obj': Punchout,
        'analysis_obj': PunchoutAnalysis
    },
    'ro_frequency_optimization': {
        'redis_field': 'ro_freq_opt',
        'qubit_state': 0,  # doesn't matter
        'measurement_obj': RO_frequency_optimization,
        'analysis_obj': OptimalROFrequencyAnalysis
    },
    'ro_frequency_optimization_gef': {
        'redis_field': 'ro_freq_opt',
        'qubit_state': 2,
        'measurement_obj': RO_frequency_optimization,
        'analysis_obj': OptimalROFrequencyAnalysis
    },
    'ro_amplitude_optimization': {
        'redis_field': 'ro_pulse_amp_opt',
        'qubit_state': 0,  # doesn't matter
        'measurement_obj': RO_amplitude_optimization,
        'analysis_obj': OptimalROAmplitudeAnalysis
    },
    'state_discrimination': {
        'redis_field': 'discriminator',
        'qubit_state': 0,  # doesn't matter
        'measurement_obj': Single_Shots_RO,
        'analysis_obj': StateDiscrimination
    },
    'coupler_spectroscopy': {
        'redis_field': '',
        'qubit_state': 0,
        'measurement_obj': Two_Tones_Spectroscopy,
        'analysis_obj': CouplerSpectroscopyAnalysis
    },
}


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    print(f'{ topo_order=}')
    print(f'{ filtered_order=}')

    # nx.draw_networkx(graph, alpha=0.5, node_color='cyan', node_size=600)
    # plt.show()

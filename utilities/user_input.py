from typing import List
import numpy as np
from uuid import uuid4
from utilities.visuals import draw_arrow_chart
from config_files.VNA_values import (
     VNA_resonator_frequencies, VNA_f01_frequencies, VNA_f12_frequencies
)


nodes = [
        # "tof",
        "resonator_spectroscopy",
        # "punchout",
        "qubit_01_spectroscopy_pulsed",
        "rabi_oscillations",
        # "T1",
        #"XY_crosstalk",
        "ramsey_correction",
        "motzoi_parameter",
        "n_rabi_oscillations",
        "resonator_spectroscopy_1",
        "qubit_12_spectroscopy_pulsed",
        "rabi_oscillations_12",
        "ramsey_correction_12",
        "resonator_spectroscopy_2",
        #"ro_frequency_optimization",
        #"ro_amplitude_optimization",
        #"state_discrimination",
        "cz_chevron",
        "cz_calibration",
        ]

qubits = [ 'q11','q12','q13','q14','q15']
# qubits = [ 'q11','q12']
# couplers = ['c1112','c1213','c1314','c1415']
#qubits = [ 'q16','q17','q18','q19','q20','q21','q22','q23','q24','q25']
#qubits = [ 'q16','q17','q19','q21','q22','q23','q25']
#qubits = [ 'q16','q17', 'q19']

N_qubits = len(qubits)

res_spec_samples = 41
qub_spec_samples = 201

def resonator_samples(qubit:str, punchout=False) -> np.ndarray:
    if qubit == 'q12':
        sweep_range = 2e6
    else:
        sweep_range = 1e6
    punchout_range = 0e6
    VNA_frequency = VNA_resonator_frequencies[qubit]
    min_freq =  VNA_frequency - sweep_range/2
    #min_freq =  min_freq if not punchout else min_freq - punchout_range
    #max_freq =  VNA_frequency + sweep_range / 2 - 2e6
    max_freq =  VNA_frequency + sweep_range / 2
    return np.linspace(min_freq, max_freq, res_spec_samples)

def qubit_samples(qubit:str, transition:str = '01') -> np.ndarray:
    sweep_range = 20e6
    if transition=='01':
        VNA_frequency = VNA_f01_frequencies[qubit]
    elif transition=='12':
        VNA_frequency = VNA_f12_frequencies[qubit]
    else :
        raise ValueError('Invalid transition')

    min_freq =  VNA_frequency - sweep_range / 2 - 0*sweep_range
    max_freq =  VNA_frequency + sweep_range / 2 + 0*sweep_range
    return np.linspace(min_freq, max_freq, qub_spec_samples)

def experiment_parameters(node:str, qubits:List[str], dummy:bool=False) -> dict:
    '''
    Dictionary that contains the parameter space for each calibration node.
    The keys order is:
    1. Node key
    2. Sweep parameter key
    3. qubit key
    For example, if the calibrtation node is 'resonator_spectroscopy'
    and we have two qubits labeled 'q1' and 'q2', it returns the dictionary:
    sweep_parameters = {
        'resonator_spectroscopy': {
             'ro_frequencies':
                  {'q1': array_of_frequencies,
                   'q2': array_of_frequencies
                  }
        }
    }
    '''
    if dummy:
        qubits = [ 'q16','q17', 'q19']

    sweep_parameters = {
        'tof': {
            'ro_acq_delay': {qubit: np.array([1,1]) for qubit in qubits}
        },

        'resonator_spectroscopy': {
            'ro_frequencies': {qubit: resonator_samples(qubit) for qubit in qubits}
        },

        'resonator_spectroscopy_1': {
            'ro_frequencies': {qubit: resonator_samples(qubit) for qubit in qubits}
        },

        'resonator_spectroscopy_2': {
            'ro_frequencies': {qubit: resonator_samples(qubit) for qubit in qubits}
        },

        'ro_frequency_optimization': {
            'ro_opt_frequencies': {qubit: resonator_samples(qubit) for qubit in qubits}
        },

        'punchout': {
            'ro_frequencies': {qubit: resonator_samples(qubit, punchout=True) for qubit in qubits},
            'ro_amplitudes': {qubit : np.linspace(4e-3, 1.2e-1, 11) for qubit in qubits}
        },

        'qubit_01_spectroscopy_pulsed': {
            'spec_frequencies': {qubit: qubit_samples(qubit) for qubit in qubits}
        },

        'qubit_12_spectroscopy_pulsed': {
            'spec_frequencies': {qubit: qubit_samples(qubit,'12') for qubit in qubits}
        },

        'rabi_oscillations': {
            'mw_amplitudes': { qubit : np.linspace(0.002,0.4,31) for qubit in qubits}
        },

        'rabi_oscillations_12': {
            'mw_amplitudes': { qubit : np.linspace(0.002,0.5,31) for qubit in qubits}
        },

        'ro_amplitude_optimization': {
            'qubit_states': {qubit: np.random.randint(0,high=2,size=100) for qubit in qubits},
            'ro_amplitudes': {qubit : np.linspace(0.005,0.039,8) for qubit in qubits}
        },

        'T1': {
            'delays': { qubit : np.arange(16e-9,250e-6,4e-6) for qubit in qubits}
        },

        'XY_crosstalk': {
            'mw_amplitudes': { qubit : np.linspace(0.002,0.22,5) for qubit in qubits },
            'mw_pulse_durations': { qubit : np.arange(20e-9,300e-9,41) for qubit in qubits },
            'drive_qubit': 'q18'
        },
        'ramsey_correction': {
            'ramsey_delays': { qubit : np.arange(4e-9, 2048e-9, 8*8e-9) for qubit in qubits },
            'artificial_detunings': { qubit : np.arange(-2.1, 2.1, 0.8)*1e6 for qubit in qubits },
        },

        'ramsey_correction_12': {
            'ramsey_delays': { qubit : np.arange(4e-9, 1*2048e-9, 4*8e-9) for qubit in qubits },
            'artificial_detunings': { qubit : np.arange(-2.1, 2.1, 0.8)*1e6 for qubit in qubits },
        },

        'motzoi_parameter': {
            'mw_motzois': {qubit: np.linspace(-0.5,0.5,61) for qubit in qubits},
            'X_repetitions': {qubit : np.arange(2, 17, 4) for qubit in qubits}
        },
        'n_rabi_oscillations': {
            'mw_amplitudes_sweep': {qubit: np.linspace(-0.1,0.1,61) for qubit in qubits},
            'X_repetitions': {qubit : np.arange(1, 16, 4) for qubit in qubits}
        },
        'state_discrimination': {
            'qubit_states': {qubit: np.random.randint(0,high=2,size=700) for qubit in qubits},
        },
        'cz_chevron': {
            'cz_pulse_frequencies_sweep': {qubit: np.linspace(-50e6,50e6,3) for qubit in qubits},
            'cz_pulse_amplitudes': {qubit: np.linspace(0.0,0.001,5) for qubit in qubits},
            # 'testing_group': 1,
            # 'cz_pulse_duration': 200e-9,
            # 'cz_pulse_width': 4e-9,
        },
        'cz_calibration': {
            'ramsey_phases': {qubit: np.linspace(0, 2*np.pi, 5) for qubit in qubits},
            'control_ons': {qubit: [False,True] for qubit in qubits},
            # 'testing_group': 1,
            # 'cz_pulse_duration': 200e-9,
            # 'cz_pulse_width': 4e-9,
        }
    }
    return sweep_parameters

# target_node = "state_discrimination"
target_node = nodes[-1]

draw_arrow_chart(f'Qubits: {N_qubits}', nodes[:nodes.index(target_node)+1])

def user_requested_calibration(node: str, dummy:bool=False):
    job = {
        "job_id": str(uuid4()),
        "name": node,
        "qubits": qubits,
        "experiment_params": experiment_parameters(node,qubits,dummy),
    }

    return job

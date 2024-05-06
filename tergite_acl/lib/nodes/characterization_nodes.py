from time import sleep

import numpy as np

from tergite_acl.lib.analysis.T1_analysis import T1Analysis, T2Analysis, T2EchoAnalysis
from tergite_acl.lib.analysis.check_cliffords_analysis import CheckCliffordsAnalysis
from tergite_acl.lib.analysis.all_XY_analysis import All_XY_Analysis
# from analysis.cz_chevron_analysis import CZChevronAnalysis, CZChevronAnalysisReset
from tergite_acl.lib.analysis.randomized_benchmarking_analysis import RandomizedBenchmarkingAnalysis
from tergite_acl.lib.node_base import BaseNode
from tergite_acl.lib.calibration_schedules.T1 import T1, T2, T2Echo
from tergite_acl.lib.calibration_schedules.check_cliffords import Check_Cliffords
from tergite_acl.lib.calibration_schedules.randomized_benchmarking import Randomized_Benchmarking
from tergite_acl.lib.calibration_schedules.all_XY import All_XY


class All_XY_Node(BaseNode):
    measurement_obj = All_XY
    analysis_obj = All_XY_Analysis

    def __init__(self, name: str, all_qubits: list[str], **node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.all_qubits = all_qubits
        self.redis_field = ['error_syndromes']
        self.backup = False
        self.schedule_samplespace = {
            'XY_index': {
                qubit: np.array(range(1,22)) for qubit in self.all_qubits
            }
        }


class T1_Node(BaseNode):
    measurement_obj = T1
    analysis_obj = T1Analysis

    def __init__(self, name: str, all_qubits: list[str], **node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.all_qubits = all_qubits
        self.redis_field = ['t1_time']
        self.backup = False

        self.type = 'parameterized_simple_sweep'
        self.node_externals = range(2)
        self.external_parameter_name = 'repeat'
        self.external_parameter_value = 0

        self.sleep_time = 3
        self.operations_args = []

        self.schedule_samplespace = {
            'delays': {
                qubit: 8e-9 + np.arange(0, 300e-6, 6e-6) for qubit in self.all_qubits
            }
        }
        self.external_samplespace = {
            'repeat': range(self.number_or_repeated_T1)
        }

    def pre_measurement_operation(self, external=1):
        if external > 0:
            print(f'sleeping for {self.sleep_time} seconds')
            sleep(self.sleep_time)

    @property
    def dimensions(self):
        return (len(self.samplespace['delays'][self.all_qubits[0]]), 1)



class Randomized_Benchmarking_Node(BaseNode):
    measurement_obj = Randomized_Benchmarking
    analysis_obj = RandomizedBenchmarkingAnalysis

    def __init__(self, name: str, all_qubits: list[str], **node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.type = 'parameterized_sweep'
        self.all_qubits = all_qubits
        self.node_dictionary = node_dictionary
        self.backup = False
        self.redis_field = ['fidelity']

        self.external_parameter_value = 0 # TODO is this necessary?

        self.schedule_samplespace = {
            'number_of_cliffords': {
                qubit: np.array(
                    [2, 16, 128, 256, 512, 768, 1024, 0, 1]
                ) for qubit in self.all_qubits
            },
        }

        self.external_samplespace = {
            'seed': np.arange(5, dtype=np.int32)
        }

    @property
    def dimensions(self):
        return (len(self.samplespace['number_of_cliffords'][self.all_qubits[0]]), 1)


# TODO this needs to be reviwed
# class Check_Cliffords_Node:
#     def __init__(self, name: str, all_qubits: list[str], **kwargs):
#         self.name = name
#         self.all_qubits = all_qubits
#         self.node_dictionary = kwargs
#         self.redis_field = ['t1_time']  # TODO Empty?
#         self.measurement_obj = Check_Cliffords
#         self.analysis_obj = CheckCliffordsAnalysis
#
#     @property
#     def samplespace(self):
#         cluster_samplespace = {
#             'clifford_indices': {
#                 qubit: np.linspace(0, 25) for qubit in self.all_qubits
#             }
#         }
#         return cluster_samplespace


class T2_Node(BaseNode):
    measurement_obj = T2
    analysis_obj = T2Analysis

    def __init__(self, name: str, all_qubits: list[str], **node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.redis_field = ['t2_time']
        self.qubit_state = 0

        self.schedule_samplespace = {
            'delays': {
                qubit: 8e-9 + np.arange(0, 100e-6, 1e-6) for qubit in self.all_qubits
            }
        }


class T2_Echo_Node(BaseNode):
    measurement_obj = T2Echo
    analysis_obj = T2EchoAnalysis

    def __init__(self, name: str, all_qubits: list[str], **node_dictionary):
        super().__init__(name, all_qubits, **node_dictionary)
        self.name = name
        self.redis_field = ['t2_time']
        self.qubit_state = 0

        self.schedule_samplespace = {
            'delays': {
                qubit: 8e-9 + np.arange(0, 300e-6, 6e-6) for qubit in self.all_qubits
            }
        }

import numpy as np
from quantify_scheduler.operations.gate_library import Measure, Reset, X90, H, X, Rxy
from quantify_scheduler.schedules.schedule import Schedule

from tergite_autocalibration.lib.base.measurement import BaseMeasurement
from tergite_autocalibration.utils.extended_gates import Rxy_12
from tergite_autocalibration.utils.extended_transmon_element import ExtendedTransmon
import tergite_autocalibration.utils.clifford_elements_decomposition as cliffords

class PurityBenchmarking(BaseMeasurement):
    def __init__(self, transmons: dict[str, ExtendedTransmon], qubit_state: int = 0):
        super().__init__(transmons)
        self.qubit_state = qubit_state
        self.transmons = transmons
        # Initialize dictionaries to store raw measurement data for each qubit
        self.raw_measurements = {qubit: {"X": [], "Y": [], "Z": []} for qubit in transmons}

    def schedule_function(
        self,
        seeds: dict[str, int],
        number_of_cliffords: dict[str, np.ndarray],
        repetitions: int = 1024,
    ) -> Schedule:
        """
        Generate a schedule for performing purity benchmarking using Clifford gates.
        The goal is to measure the purity of the qubit states after applying each sequence of Clifford gates.

        Schedule sequence:
            Reset -> Apply Clifford operations -> Measure X -> Reset -> Apply Clifford operations -> Measure Y
            -> Reset -> Apply Clifford operations -> Measure Z

        Parameters:
        ----------
        repetitions: int
            The number of times the Schedule will be repeated.
        number_of_cliffords: dict[str, np.ndarray]
            The number of random Clifford operations applied on each qubit state.
            This parameter is swept over.

        Returns:
        -------
        Schedule:
            An experiment schedule.
        """  
        # Create a new Schedule object with the specified number of repetitions
        schedule = Schedule("purity_benchmarking", repetitions)
        qubits = self.transmons.keys()
        # This is the common reference operation so the qubits can be operated in parallel
        root_relaxation = schedule.add(Reset(*qubits), label="Start")
        
        for this_qubit, clifford_sequence_lengths in number_of_cliffords.items():
            # Get the total number of Clifford gate decompositions available
            all_cliffords = len(cliffords.XY_decompositions)
            # Use the seed for reproducibility of random sequences
            seed = seeds[this_qubit]
            rng = np.random.default_rng(seed)
            schedule.add(Reset(*qubits), ref_op=root_relaxation, ref_pt="end")

            for acq_index, this_number_of_cliffords in enumerate(clifford_sequence_lengths[:-21]):
                # Generate a random sequence of Clifford operations
                random_sequence = rng.integers(all_cliffords, size=this_number_of_cliffords) // 24

                def apply_clifford_sequence(schedule, qubit, random_sequence):
                    # Apply a sequence of Clifford operations to the qubit
                    for sequence_index in random_sequence:
                        physical_gates = cliffords.XY_decompositions[sequence_index]
                        for gate_angles in physical_gates.values():
                            theta = gate_angles["theta"]
                            phi = gate_angles["phi"]
                            schedule.add(Rxy(qubit=qubit, theta=theta, phi=phi))
                    return schedule

                # Measure in X basis
                apply_clifford_sequence(schedule, this_qubit, random_sequence)
                schedule.add(H(this_qubit))  # Prepare for X basis measurement
                schedule.add(Measure(this_qubit, acq_index=3*acq_index))
                schedule.add(Reset(this_qubit))

                # Measure in Y basis
                apply_clifford_sequence(schedule, this_qubit, random_sequence)
                schedule.add(X90(this_qubit))  # Prepare for Y basis measurement
                schedule.add(Measure(this_qubit, acq_index=3*acq_index+1))
                schedule.add(Reset(this_qubit))

                # Measure in Z basis
                apply_clifford_sequence(schedule, this_qubit, random_sequence)
                schedule.add(Measure(this_qubit, acq_index=3*acq_index+2))
                schedule.add(Reset(this_qubit))

            # Add calibration points for the qubit
            calibration_acq_index = len(clifford_sequence_lengths[:-21])*3

            schedule.add(Reset(this_qubit))
            schedule.add(Reset(this_qubit))
            schedule.add(Measure(this_qubit, acq_index=calibration_acq_index))
            schedule.add(Reset(this_qubit))

            schedule.add(Reset(this_qubit))
            schedule.add(Reset(this_qubit))
            schedule.add(X(this_qubit))
            schedule.add(Measure(this_qubit, acq_index=calibration_acq_index + 1))
            schedule.add(Reset(this_qubit))

            schedule.add(Reset(this_qubit))
            schedule.add(Reset(this_qubit))
            schedule.add(X(this_qubit))
            schedule.add(Rxy_12(this_qubit))
            schedule.add(Measure(this_qubit, acq_index=calibration_acq_index + 2))
            schedule.add(Reset(this_qubit))

        return schedule
"""
Module containing a schedule class for T1 and T2 coherence time measurement.
"""
from quantify_scheduler.enums import BinMode
from quantify_scheduler import Schedule
from quantify_scheduler.operations.gate_library import Measure, Reset, X, X90
from calibration_schedules.measurement_base import Measurement
import numpy as np

class T1(Measurement):

    def __init__(self,transmons,qubit_state:int=0):
        super().__init__(transmons)
        self.qubit_state = qubit_state
        self.transmons = transmons

        self.static_kwargs = {
            'qubits': self.qubits,
        }

    def schedule_function(
        self,
        qubits: list[str],
        delays: dict[str, np.ndarray],
        repetitions: int = 1024,
    ) -> Schedule:
        """
        Generate a schedule for performing a T1 experiment measurement to find the relaxation time T_1 for multiple qubits.

        Schedule sequence
            Reset -> pi pulse -> Idel(tau) -> Measure
        
        Parameters
        ----------
        self
            Contains all qubit states.
        qubits
            The list of qubits on which to perform the experiment.
        delays
            Array of the sweeping delay times tau between the pi-pulse and the measurement for each qubit.
        repetitions
            The amount of times the Schedule will be repeated.
        
        Returns
        -------
        :
            An experiment schedule.
        """
        schedule = Schedule("multiplexed_T1",repetitions)

        #This is the common reference operation so the qubits can be operated in parallel
        root_relaxation = schedule.add(Reset(*qubits), label="Start")
        
        #First loop over every qubit with corresponding tau sweeping lists
        for this_qubit, times_val in delays.items():
            schedule.add(
                Reset(*qubits), ref_op=root_relaxation, ref_pt='end'
            )  # To enforce parallelism we refer to the root relaxation

            #Second loop over all tau delay values
            for acq_index, tau in enumerate(times_val):
                schedule.add(X(this_qubit))
                schedule.add(
                    Measure(this_qubit, acq_index=acq_index, bin_mode=BinMode.AVERAGE),
                    ref_pt="end",
                    rel_time=tau,
                )
                schedule.add(Reset(this_qubit))
        return schedule

class T2(Measurement):

    def __init__(self,transmons,qubit_state:int=0):
        super().__init__(transmons)
        self.qubit_state = qubit_state
        self.transmons = transmons

        self.static_kwargs = {
            'qubits': self.qubits,
        }

    def schedule_function(
        self,
        qubits: list[str],
        delays: dict[str, np.ndarray],
        repetitions: int = 1024,
    ) -> Schedule:
        """
        Generate a schedule for performing a T2 experiment measurement to find the coherence time T_2 for multiple qubits.

        Schedule sequence
            Reset -> pi/2 pulse -> Idel(tau) -> pi/2 pulse -> Measure
        
        Parameters
        ----------
        self
            Contains all qubit states.
        qubits
            The list of qubits on which to perform the experiment.
        delays
            Array of the sweeping delay times tau between the pi/2-pulse and the other pi/2-pulse for each qubit.
        repetitions
            The amount of times the Schedule will be repeated.
        
        Returns
        -------
        :
            An experiment schedule.
        """
        schedule = Schedule("multiplexed_T1",repetitions)

        #This is the common reference operation so the qubits can be operated in parallel
        root_relaxation = schedule.add(Reset(*qubits), label="Start")
        
        #First loop over every qubit with corresponding tau sweeping lists
        for this_qubit, times_val in delays.items():
            schedule.add(
                Reset(*qubits), ref_op=root_relaxation, ref_pt='end'
            )  # To enforce parallelism we refer to the root relaxation

            #Second loop over all tau delay values
            for acq_index, tau in enumerate(times_val):
                schedule.add(X90(this_qubit))
                schedule.add(X90(this_qubit),
                    ref_pt="end",
                    rel_time=tau,)
                schedule.add(
                    Measure(this_qubit, acq_index=acq_index, bin_mode=BinMode.AVERAGE)
                )
                schedule.add(Reset(this_qubit))
        return schedule

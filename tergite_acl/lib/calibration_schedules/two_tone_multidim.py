"""
Module containing a schedule class for two-tone (qubit) spectroscopy calibration.
"""
from quantify_scheduler.enums import BinMode
from quantify_scheduler.operations.gate_library import Measure, Reset, X
from quantify_scheduler.operations.pulse_library import SetClockFrequency, SoftSquarePulse
from quantify_scheduler.operations.pulse_factories import long_square_pulse
from quantify_scheduler.resources import ClockResource
from quantify_scheduler.schedules.schedule import Schedule
from tergite_acl.utils.extended_transmon_element import ExtendedTransmon, Measure_RO1
import numpy as np

from tergite_acl.lib.measurement_base import Measurement

class Two_Tones_Multidim(Measurement):

    def __init__(self,transmons: dict[str, ExtendedTransmon], qubit_state:int=0):
        super().__init__(transmons)

        self.qubit_state = qubit_state
        self.transmons = transmons

    def schedule_function(
        self,
        spec_frequencies: dict[str,np.ndarray],
        spec_pulse_amplitudes: dict[str,np.ndarray] = None,

        repetitions: int = 1024,
        ) -> Schedule:
        """
        Generate a schedule for performing two-tone (qubit) spectroscopy to locate the qubits resonance frequency for multiple qubits.

        Schedule sequence
            Reset -> Spectroscopy pulse -> Measure

        Parameters
        ----------
        repetitions
            The amount of times the Schedule will be repeated.

        Returns
        -------
        :
            An experiment schedule.
        """

        # if port_out is None: port_out = port
        schedule = Schedule("multiplexed_qubit_spec",repetitions)

        # Initialize the clock for each qubit
        #Initialize ClockResource with the first frequency value
        for this_qubit, spec_array_val in spec_frequencies.items():
            if self.qubit_state == 0:
                schedule.add_resource( ClockResource(name=f'{this_qubit}.01', freq=spec_array_val[0]) )
            elif self.qubit_state == 1:
                schedule.add_resource( ClockResource(name=f'{this_qubit}.12', freq=spec_array_val[0]) )
            else:
                raise ValueError(f'Invalid qubit state: {self.qubit_state}')

        #This is the common reference operation so the qubits can be operated in parallel
        qubits = self.transmons.keys()

        if self.qubit_state == 0:
            measure_function = Measure
        elif self.qubit_state == 1:
            measure_function = Measure_RO1
        else:
            raise ValueError(f'Invalid qubit state: {self.qubit_state}')

        root_relaxation = schedule.add(Reset(*qubits), label="Reset")

        # The outer loop, iterates over all qubits
        for this_qubit, spec_pulse_frequency_values in spec_frequencies.items():

            # unpack the static parameters
            this_transmon = self.transmons[this_qubit]
            spec_pulse_duration = this_transmon.spec.spec_duration()
            mw_pulse_port = this_transmon.ports.microwave()

            if spec_pulse_amplitudes is None:
                spec_amplitude = this_transmon.spec.spec_ampl_optimal()
                print(f'setting optimal spec spec_amplitude for {this_qubit} {spec_amplitude}')
                amplitude_values = [spec_amplitude]

            # assign qubit spectroscopy pulse based on duration so long pulses can fit in memory
            if spec_pulse_duration > 6e-6:
                SpectroscopyPulse = long_square_pulse
            else:
                SpectroscopyPulse = SoftSquarePulse


            if self.qubit_state == 0:
                this_clock = f'{this_qubit}.01'
            elif self.qubit_state == 1:
                this_clock = f'{this_qubit}.12'
            else:
                raise ValueError(f'Invalid qubit state: {self.qubit_state}')

            amplitude_values = spec_pulse_amplitudes[this_qubit]

            number_of_ampls = len(amplitude_values)

            schedule.add(
                Reset(*qubits), ref_op=root_relaxation, ref_pt='end'
            ) #To enforce parallelism we refer to the root relaxation

            #The intermediate loop iterates over all frequency values in the frequency batch:
            for freq_indx, spec_pulse_frequency in enumerate(spec_pulse_frequency_values):

                #reset the clock frequency for the qubit pulse
                set_frequency = schedule.add(
                    SetClockFrequency(clock=this_clock, clock_freq_new=spec_pulse_frequency),
                )

                # The inner loop, iterates over all spec_amplitudes
                for acq_index, spec_pulse_amplitude in enumerate(amplitude_values):
                    this_index = freq_indx * number_of_ampls + acq_index

                    if self.qubit_state == 0:
                        pass
                    elif self.qubit_state == 1:
                        schedule.add(X(this_qubit))
                    else:
                        raise ValueError(f'Invalid qubit state: {self.qubit_state}')

                    # long pulses require more efficient memory managment
                    if spec_pulse_duration > 6.5e-6:
                        SpectroscopyPulse = long_square_pulse
                    else:
                        SpectroscopyPulse = SoftSquarePulse

                    print(f'{ SpectroscopyPulse = }')
                    print(f'{ spec_pulse_duration = }')
                    schedule.add(
                        SpectroscopyPulse(
                            duration=spec_pulse_duration,
                            amp=spec_pulse_amplitude,
                            port=mw_pulse_port,
                            clock=this_clock,
                        ),
                    )

                    schedule.add(
                        measure_function(this_qubit, acq_index=this_index,bin_mode=BinMode.AVERAGE),
                    )

                    # update the relaxation for the next batch point
                    schedule.add(Reset(this_qubit))

        return schedule

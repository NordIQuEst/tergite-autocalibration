from quantify_scheduler.enums import BinMode
from quantify_scheduler.operations.acquisition_library import SSBIntegrationComplex
from quantify_scheduler.operations.gate_library import Measure, Reset, X
from quantify_scheduler.operations.pulse_library import SetClockFrequency, SoftSquarePulse
from quantify_scheduler.resources import ClockResource
from quantify_scheduler.schedules.schedule import Schedule

from calibration_schedules.measurement_base import Measurement
# from transmon_element import Measure_1


class Two_Tones_Spectroscopy(Measurement):

    def __init__(self,transmons,qubit_state:int=0):
        super().__init__(transmons)

        self.qubit_state = qubit_state
        self.transmons = transmons

        self.static_kwargs = {
            'qubits': self.qubits,
            'mw_pulse_durations': self.attributes_dictionary('duration'),
            'mw_pulse_amplitudes': self.attributes_dictionary('amp180'),
            'mw_pulse_ports': self.attributes_dictionary('microwave'),
            'mw_clocks': self.attributes_dictionary('f01'),

            'ro_pulse_amplitudes': self.attributes_dictionary('ro_pulse_amp'),
            'ro_pulse_durations' : self.attributes_dictionary('ro_pulse_duration'),
            'ro_frequencies': self.attributes_dictionary('ro_freq'),
            'ro_frequencies_1': self.attributes_dictionary('ro_freq_1'),
            'integration_times': self.attributes_dictionary('ro_acq_integration_time'),
            'acquisition_delays': self.attributes_dictionary('ro_acq_delay'),
            'ports': self.attributes_dictionary('ro_port'),
        }


    def schedule_function(
            self,
            qubits: list[str],
            mw_pulse_durations: dict[str,float],
            mw_pulse_amplitudes: dict[str,float],
            mw_pulse_ports: dict[str,str],
            mw_clocks: dict[str,str],

            ro_pulse_amplitudes: dict[str,float],
            ro_pulse_durations: dict[str,float],
            ro_frequencies: dict[str,float],
            ro_frequencies_1: dict[str,float],
            integration_times: dict[str,float],
            acquisition_delays: dict[str,float],
            ports: dict[str,str],

            repetitions: int = 1024,
            **spec_pulse_frequencies,
        ) -> Schedule:

        # if port_out is None: port_out = port
        sched = Schedule("multiplexed_qubit_spec_NCO",repetitions)
        # Initialize the clock for each qubit
        for spec_key, spec_array_val in spec_pulse_frequencies.items():
            this_qubit = [qubit for qubit in qubits if qubit in spec_key][0]

            sched.add_resource(
                ClockResource( name=f'{this_qubit}.01', freq=spec_array_val[0]),
            )

        #This is the common reference operation so the qubits can be operated in parallel
        root_relaxation = sched.add(Reset(*qubits), label="Reset")

        # The first for loop iterates over all qubits:
        for acq_cha, (spec_key, spec_array_val) in enumerate(spec_pulse_frequencies.items()):
            this_qubit = [qubit for qubit in qubits if qubit in spec_key][0]

            #if self.qubit_state==0:
            #    this_ro_frequency = ro_frequencies[this_qubit]
            #elif self.qubit_state==1:
            #    this_ro_frequency = ro_frequencies_1[this_qubit]
            #else:
            #    raise ValueError(f'Invalid qubit state: {self.qubit_state}')

            #sched.add_resource( ClockResource(name=f'{this_qubit}.ro', freq=this_ro_frequency) )

            # The second for loop iterates over all frequency values in the frequency batch:
            relaxation = root_relaxation #To enforce parallelism we refer to the root relaxation
            for acq_index, spec_pulse_frequency in enumerate(spec_array_val):
                #reset the clock frequency for the qubit pulse
                set_frequency = sched.add(
                    SetClockFrequency(clock=f'{this_qubit}.01', clock_freq_new=spec_pulse_frequency),
                    label=f"set_freq_{this_qubit}_{acq_index}",
                    ref_op=relaxation, ref_pt='end'
                )

                if self.qubit_state == 0:
                    excitation_pulse = set_frequency
                elif self.qubit_state == 1:
                    excitation_pulse = sched.add(X(this_qubit), ref_op=set_frequency, ref_pt='end')
                else:
                    raise ValueError(f'Invalid qubit state: {self.qubit_state}')

                #spectroscopy pulse
                spec_pulse = sched.add(
                    SoftSquarePulse(
                        duration= mw_pulse_durations[this_qubit],
                        amp= mw_pulse_amplitudes[this_qubit],
                        port= mw_pulse_ports[this_qubit],
                        clock=f'{this_qubit}.01',
                    ),
                    label=f"spec_pulse_{this_qubit}_{acq_index}", ref_op=excitation_pulse, ref_pt="end",
                )

                if self.qubit_state == 0:
                    measure_function = Measure
                # elif self.qubit_state == 1:
                #     measure_function = Measure_1

                sched.add(
                    measure_function(this_qubit, acq_channel=acq_cha, acq_index=acq_index,bin_mode=BinMode.AVERAGE),
                    ref_op=spec_pulse,
                    ref_pt='end',
                    label=f'Measurement_{this_qubit}_{acq_index}'
                )

                # print(f'{ measure_function.items(measure_function) = }')
                # print(f'{ this_clock = }')
                # print(f'{ this_ro_frequency = }')

                #ro_pulse = sched.add(
                #    SquarePulse(
                #        duration=ro_pulse_durations[this_qubit],
                #        amp=ro_pulse_amplitudes[this_qubit],
                #        port=ports[this_qubit],
                #        clock=this_clock,
                #    ),
                #    label=f"ro_pulse_{this_qubit}_{acq_index}", ref_op=spec_pulse, ref_pt="end",
                #)


                #sched.add(
                #    SSBIntegrationComplex(
                #        duration=integration_times[this_qubit],
                #        port=ports[this_qubit],
                #        clock=this_clock,
                #        acq_index=acq_index,
                #        acq_channel=acq_cha,
                #        bin_mode=BinMode.AVERAGE
                #    ),
                #    ref_op=ro_pulse, ref_pt="start",
                #    rel_time=acquisition_delays[this_qubit],
                #    label=f"acquisition_{this_qubit}_{acq_index}",
                #)


                # update the relaxation for the next batch point
                relaxation = sched.add(Reset(this_qubit), label=f"Reset_{this_qubit}_{acq_index}")

        return sched

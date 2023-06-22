from quantify_scheduler.resources import ClockResource
from quantify_scheduler import Schedule
from quantify_scheduler.operations.pulse_library import DRAGPulse
from quantify_scheduler.operations.gate_library import Measure, Reset
from measurements_base import Measurement_base

class Motzoi_parameter_BATCHED(Measurement_base):

    def __init__(self,transmons,connections):
        super().__init__(transmons,connections)
        self.experiment_parameters = ['mw_motzoi_BATCHED', 'X_repetition'] # The order maters
        self.parameter_order = ['mw_motzoi_BATCHED', 'X_repetition'] # The order maters
        self.gettable_batched = True
        self.static_kwargs = {
            'qubits': self.qubits,
            'mw_frequencies': self._get_attributes('freq_01'),
            'mw_amplitudes': self._get_attributes('mw_amp180'),
            'mw_clocks': self._get_attributes('mw_01_clock'),
            'mw_pulse_ports': self._get_attributes('mw_port'),
            'mw_pulse_durations': self._get_attributes('mw_pulse_duration'),
        }

    def settables_dictionary(self):
        parameters = self.experiment_parameters
        manual_parameter = 'mw_motzoi_BATCHED'
        assert( manual_parameter in self.experiment_parameters )
        mp_data = {
            manual_parameter : {
                'name': manual_parameter,
                'initial_value': 1e-4,
                'unit': 'V',
                'batched': True
            }
        }
        manual_parameter = 'X_repetition'
        assert( manual_parameter in self.experiment_parameters )
        mp_data.update( {
            manual_parameter: {
                'name': manual_parameter,
                'initial_value': 1,
                'unit': '-',
                'batched': False
            }
        })
        return self._settables_dictionary(parameters, isBatched=self.gettable_batched, mp_data=mp_data)

    def setpoints_array(self):
        return self._setpoints_Nd_array()

    def schedule_function(
            self,
            qubits: list[str],
            mw_frequencies: dict[str,float],
            mw_amplitudes: dict[str,float],
            mw_pulse_ports: dict[str,str],
            mw_clocks: dict[str,str],
            mw_pulse_durations: dict[str,float],
            repetitions: int = 1024,
            **mw_motzois,
        ) -> Schedule:
        schedule = Schedule("mltplx_motzoi",repetitions)

        for mw_f_key, mw_f_val in mw_frequencies.items():
            this_qubit = [q for q in qubits if q in mw_f_key][0]
            schedule.add_resource(
                ClockResource(name=mw_clocks[this_qubit], freq=mw_f_val)
            )
        values = {qubit:{} for qubit in qubits}
        for motzoi_key, motzoi_val in mw_motzois.items():
            this_qubit = [q for q in qubits if q in motzoi_key][0]
            if 'X_repetition' in motzoi_key:
               values[this_qubit].update({'X_repetition':motzoi_val})
            if 'mw_motzoi' in motzoi_key:
               values[this_qubit].update({'mw_motzoi':motzoi_val})

        #This is the common reference operation so the qubits can be operated in parallel
        root_relaxation = schedule.add(Reset(*qubits), label="Reset")

        for acq_cha, (values_key, values_val) in enumerate(values.items()):
            this_qubit = [q for q in qubits if q in values_key][0]

            X_repetitions = values_val['X_repetition']
            X_repetitions = int(X_repetitions)
            motzoi_parameter_values = values_val['mw_motzoi']

            # The second for loop iterates over all frequency values in the frequency batch:
            relaxation = schedule.add(
                Reset(*qubits), label=f'Reset_{acq_cha}', ref_op=root_relaxation, ref_pt_new='end'
            ) #To enforce parallelism we refer to the root relaxation

            for acq_index, mw_motzoi in enumerate(motzoi_parameter_values):
                for x_index in range(X_repetitions):
                    schedule.add(
                        DRAGPulse(
                            duration=mw_pulse_durations[this_qubit],
                            G_amp=mw_amplitudes[this_qubit],
                            D_amp=mw_motzoi,
                            port=mw_pulse_ports[this_qubit],
                            clock=mw_clocks[this_qubit],
                            phase=0,
                        ),
                        label=f"motzoi_drag_pulse_{this_qubit}_{x_index}_{acq_index}",
                    )
                    # inversion pulse requires 180 deg phase
                    schedule.add(
                        DRAGPulse(
                            duration=mw_pulse_durations[this_qubit],
                            G_amp=mw_amplitudes[this_qubit],
                            D_amp=mw_motzoi,
                            port=mw_pulse_ports[this_qubit],
                            clock=mw_clocks[this_qubit],
                            phase=180,
                        ),
                        label=f"motzoi_inverse_drag_pulse_{this_qubit}_{x_index}_{acq_index}",
                    )

                schedule.add(
                    Measure(this_qubit, acq_channel=acq_cha, acq_index=acq_index),
                    label=f"Measurement_{acq_index}_{acq_cha}_{this_qubit}"
                )

                schedule.add(Reset(this_qubit), label=f"Reset_{this_qubit}_{acq_index}")

        return schedule

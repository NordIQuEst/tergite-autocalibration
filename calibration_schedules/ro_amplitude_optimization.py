from quantify_scheduler.operations.gate_library import Reset, X, Rxy
from quantify_scheduler.operations.pulse_library import SquarePulse, SetClockFrequency
from quantify_scheduler.operations.acquisition_library import SSBIntegrationComplex
from quantify_scheduler.schedules.schedule import Schedule
from quantify_scheduler.operations.pulse_library import DRAGPulse
from quantify_scheduler.resources import ClockResource
from calibration_schedules.measurement_base import Measurement
from quantify_scheduler.enums import BinMode
import numpy as np

class RO_amplitude_optimization(Measurement):

    def __init__(self,transmons,qubit_state:int=0):
        super().__init__(transmons)

        self.transmons = transmons
        self.static_kwargs = {
            'qubits': self.qubits,
            'freqs_12': self.attributes_dictionary('f12'),
            'mw_ef_amp180s': self.attributes_dictionary('ef_amp180'),
            'mw_pulse_durations': self.attributes_dictionary('duration'),
            'mw_pulse_ports': self.attributes_dictionary('microwave'),
            'pulse_amplitudes': self.attributes_dictionary('pulse_amp'),
            'acquisition_delays': self.attributes_dictionary('acq_delay'),
            'integration_times': self.attributes_dictionary('integration_time'),
            'ro_ports': self.attributes_dictionary('readout_port'),
        }

    def schedule_function(
        self,
        qubits : list[str],
        freqs_12:  dict[str,float],
        mw_ef_amp180s: dict[str,float],
        mw_pulse_durations: dict[str,float],
        mw_pulse_ports: dict[str,str],
        pulse_durations: dict[str,float],
        acquisition_delays: dict[str,float],
        integration_times: dict[str,float],
        ro_ports: dict[str,str],
        ro_amplitudes: dict[str,np.ndarray],
        qubit_states: dict[str,np.ndarray],
        repetitions: int = 1,
        ) -> Schedule:
        schedule = Schedule("ro_amplitude_optimization", repetitions)

        number_of_levels = len(qubit_states)

        root_relaxation = schedule.add(Reset(*qubits), label="Reset")

        # The outer for-loop iterates over all qubits:
        for acq_cha, (this_qubit, ro_amplitude_values) in enumerate(ro_amplitudes.items()):

            this_ro_clock = f'{this_qubit}.' + 'ro_opt'

            schedule.add(
                Reset(*qubits), ref_op=root_relaxation, ref_pt_new='end'
            ) #To enforce parallelism we refer to the root relaxation

            # The intermediate for-loop iterates over all ro_amplitudes:
            for ampl_indx, ro_amplitude in enumerate(ro_amplitude_values):
                # The inner for-loop iterates over all qubit levels:
                for level_index, state_level in enumerate(qubit_states):
                    this_index = ampl_indx*number_of_levels + level_index

                    # require an integer
                    assert(type(state_level)==np.int64)

                    if state_level == 0:
                        # Not really necessary to use Rxy(0,0) we can just pass
                        schedule.add(
                            Rxy(theta=0, phi=0, qubit=this_qubit),
                        )
                    elif state_level == 1:
                        schedule.add(X(this_qubit))
                    elif state_level == 2:
                        pass
                        # schedule.add(X(qubit = this_qubit))
                        # schedule.add(
                        #     #TODO DRAG optimize for 1 <-> 2
                        #     DRAGPulse(
                        #         duration=mw_pulse_durations[this_qubit],
                        #         G_amp=mw_ef_amp180s[this_qubit],
                        #         D_amp=0,
                        #         port=mw_pulse_ports[this_qubit],
                        #         clock=mw_clocks_12[this_qubit],
                        #         phase=0,
                        #     ),
                        # )
                    else:
                        raise ValueError('State Input Error')

                    ro_pulse = schedule.add(
                        SquarePulse(
                            duration=pulse_durations[this_qubit],
                            amp=ro_amplitude,
                            port=ro_ports[this_qubit],
                            clock=this_ro_clock,
                        ),
                    )

                    schedule.add(
                        SSBIntegrationComplex(
                            duration=integration_times[this_qubit],
                            port=ro_ports[this_qubit],
                            clock=this_ro_clock,
                            acq_index=this_index,
                            acq_channel=acq_cha,
                            bin_mode=BinMode.AVERAGE
                        ),
                        ref_op=ro_pulse, ref_pt="start",
                        rel_time=acquisition_delays[this_qubit],
                    )

                    schedule.add(Reset(this_qubit))

        return schedule

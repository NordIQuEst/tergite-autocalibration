"""
Module containing a schedule class for Ramsey calibration. (1D parameter sweep, for 2D see ramsey_detunings.py)
"""
from quantify_scheduler.enums import BinMode
from quantify_scheduler import Schedule
from quantify_scheduler.operations.gate_library import Measure, Reset, X90, Rxy, X, CZ
from quantify_scheduler.operations.pulse_library import GaussPulse,SuddenNetZeroPulse,ResetClockPhase,IdlePulse,DRAGPulse,SetClockFrequency,NumericalPulse,SoftSquarePulse,SquarePulse
from quantify_scheduler.operations.pulse_library import RampPulse,DRAGPulse,SetClockFrequency,NumericalPulse,SoftSquarePulse,SquarePulse, ResetClockPhase
from quantify_scheduler.resources import ClockResource
from tergite_acl.lib.measurement_base import Measurement
from tergite_acl.utils.extended_transmon_element import Measure_RO1, Rxy_12
from tergite_acl.config.coupler_config import edge_group, qubit_types
from matplotlib import pyplot as plt
from tergite_acl.utils.extended_coupler_edge import CompositeSquareEdge
from tergite_acl.utils.extended_transmon_element import ExtendedTransmon

import numpy as np
import redis

class Reset_chevron_dc(Measurement):
    # for testing dc reset

    def __init__(self, transmons: dict[str, ExtendedTransmon],couplers: dict[str, CompositeSquareEdge], qubit_state: int = 0):
        super().__init__(transmons)
        self.transmons = transmons
        self.qubit_state = qubit_state
        self.couplers = couplers                                                                 

    def schedule_function(
            self,
            cz_pulse_amplitudes: dict[str,np.ndarray],
            cz_pulse_durations: dict[str,np.ndarray],
            duration_offset: float = 0,
            repetitions: int = 1024,
        ) -> Schedule:

        """
        Generate a schedule for performing a Ramsey fringe measurement on multiple qubits.
        Can be used both to finetune the qubit frequency and to measure the qubit dephasing time T_2. (1D parameter sweep)

        Schedule sequence
            Reset -> pi/2-pulse -> Idle(tau) -> pi/2-pulse -> Measure

        Parameters
        ----------
        self
            Contains all qubit states.
        qubits
            A list of two qubits to perform the experiment on. i.e. [['q1','q2'],['q3','q4'],...]
        mw_clocks_12
            Clocks for the 12 transition frequency of the qubits.
        mw_ef_amps180
            Amplitudes used for the excitation of the qubits to calibrate for the 12 transition.
        mw_frequencies_12
            Frequencies used for the excitation of the qubits to calibrate for the 12 transition.
        mw_pulse_ports
            Location on the device where the pulsed used for excitation of the qubits to calibrate for the 12 transition is located.
        mw_pulse_durations
            Pulse durations used for the excitation of the qubits to calibrate for the 12 transition.
        cz_pulse_frequency
            The frequency of the CZ pulse.
        cz_pulse_amplitude
            The amplitude of the CZ pulse.
        cz_pulse_duration
            The duration of the CZ pulse.
        cz_pulse_width
            The width of the CZ pulse.
        testing_group
            The edge group to be tested. 0 means all edges.
        repetitions
            The amount of times the Schedule will be repeated.

        Returns
        -------
        :
            An experiment schedule.
        """

        def local_analytic(t, a, g, c):
            numerator =  - 8 * g * (a * g * t + c)
            denominator = np.sqrt(abs(1 - 16 * (a * g * t) ** 2 - 32 * a * g * t * c - 16 * c ** 2))
            y = numerator / denominator
            return y

        def generate_local_adiabatic_pulse(g, T, y0, yt, dt = 0.1):
            c = - y0 / np.sqrt(64 * g ** 2 + 16 * y0 ** 2)
            a = (- 4 * c * (4 * g ** 2 + yt ** 2) - yt * np.sqrt(4 * g ** 2 + yt ** 2)) / (4 * g * T * (4 * g ** 2 + yt ** 2))
            # times = np.arange(0, T, dt)
            times = np.linspace(0, T, int(np.ceil(T / dt)))
            seq = local_analytic(times, a, g, c)

            return seq

        def generate_local_adiabatic_fc(g, duration, f0, ft, fq, dt = 1.):

            y0 = fq - f0
            yt = fq - ft
            seq_fq_fc_detuning = generate_local_adiabatic_pulse(g, duration, y0, yt, dt=dt)
            seq_fc_f0_detuning = - seq_fq_fc_detuning + fq - f0

            return seq_fc_f0_detuning *1e-1
            
        schedule = Schedule("reset_chevron",repetitions)
        coupler = list(self.couplers.keys())[0]
        qubits = coupler.split(sep='_')

        # cz_frequency_values = np.array(list(cz_pulse_frequencies_sweep.values())[0])
        reset_duration_values = list(cz_pulse_durations.values())[0]
        reset_pulse_amplitude_values = list(cz_pulse_amplitudes.values())[0]
        # print(f'{ reset_duration_values = }')
        # print(f'{ reset_pulse_amplitude_values = }')

        # print(f'{ cz_frequency_values[0] = }')

        # schedule.add_resource(
        #     ClockResource(name=coupler+'.cz',freq= - cz_frequency_values[0] + 4.4e9)
        # )

        # schedule.add_resource(
        #     ClockResource(name=coupler+'.cz',freq= 4.4e9)
        # )

        schedule.add_resource(
            ClockResource(name=coupler+'.cz',freq= 0e9)
        )

        number_of_durations = len(reset_duration_values)

        # The outer loop, iterates over all cz_frequencies
        for freq_index, reset_amplitude in enumerate(reset_pulse_amplitude_values):
            cz_clock = f'{coupler}.cz'
            cz_pulse_port = f'{coupler}:fl'
            # schedule.add(
            #     SetClockFrequency(clock=cz_clock, clock_freq_new= - cz_frequency + 4.4e9),
            # )
            # schedule.add(
            #     SetClockFrequency(clock=cz_clock, clock_freq_new=4.4e9),
            # )

            #The inner for loop iterates over cz pulse durations
            for acq_index, reset_duration in enumerate(reset_duration_values):
                this_index = freq_index * number_of_durations + acq_index

                relaxation = schedule.add(Reset(*qubits))

                for this_qubit in qubits:
                    # schedule.add(X(this_qubit), ref_op=relaxation, ref_pt='end')
                    if qubit_types[this_qubit] == 'Target':
                        # schedule.add(IdlePulse(40e-9), ref_op=relaxation, ref_pt='end')
                        # schedule.add(IdlePulse(20e-9))
                        schedule.add(X(this_qubit), ref_op=relaxation, ref_pt='end')
                        # schedule.add(Rxy_12(this_qubit))
                    else:
                        # schedule.add(Rxy_12(this_qubit))
                        # schedule.add(IdlePulse(40e-9))
                        # schedule.add(IdlePulse(40e-9), ref_op=relaxation, ref_pt='end')
                        # schedule.add(X(this_qubit))
                        schedule.add(X(this_qubit), ref_op=relaxation, ref_pt='end')


                schedule.add(ResetClockPhase(clock=coupler+'.cz'))

                for i in range(1):
                    # step 1 - calibrate ge/f reset qc pulse

                    buffer = schedule.add(IdlePulse(4e-9))
                    # qc = schedule.add(
                    #             RampPulse(
                    #                 offset = reset_amplitude,
                    #                 duration = reset_duration,
                    #                 amp = -reset_amplitude,
                    #                 # amp = 0.,
                    #                 port = cz_pulse_port,
                    #                 clock = cz_clock,
                    #             ),
                    #         )
                    # buffer = schedule.add(IdlePulse(4e-9),ref_op=buffer, ref_pt='end',rel_time = np.ceil( reset_duration * 1e9 / 4) * 4e-9)


                    # buffer = schedule.add(IdlePulse(np.ceil( reset_duration* 1e9 / 4) * 4e-9))

                    fq = 4.50  # qubit frequncy in GHz
                    dt = 1.0  # AWG sampling rate in nanosecond 

########################################################################################################################################################
                    # q23_q24
                    # # sweep f0, ft
                    # e
                    # f0 = fq+reset_amplitude# Initial coupler frequency in GHz
                    # ft = fq+reset_duration# Final coupler frequency in GJ+Hz
                    # g = 0.05  # = coupling strength
                    # duration = (9)  # Pulse duration in nanosecond
                    # f
                    # f0 = fq+reset_amplitude# Initial coupler frequency in GHz
                    # ft = fq+reset_duration# Final coupler frequency in GJ+Hz
                    # g = 0.075  # = coupling strength
                    # duration = (40)  # Pulse duration in nanosecond

                    # # sweep f0, t
                    # f0 = fq+reset_amplitude# Initial coupler frequency in GHz
                    # ft = fq-0.195# Final coupler frequency in GJ+Hz
                    # g = 0.0415  # = coupling strength
                    # duration = (reset_duration)*1e9  # Pulse duration in nanosecond

                    # sweep g, t
                    # e
                    # f0 = fq+0.935 # Ini1tial coupler frequency in GHz
                    # ft = fq-0.3# Final coupler frequency in GJ+Hz
                    # g = reset_amplitude  # = coupling strength
                    # duration = (reset_duration)*1e9  # Pulse duration in nanosecond
                    # f
                    # f0 = fq+0.974 # Ini1tial coupler frequency in GHz
                    # ft = fq-0.3# Final coupler frequency in GJ+Hz
                    # g = reset_amplitude  # = coupling strength
                    # duration = (reset_duration)*1e9  # Pulse duration in nanosecond

                    # sweep ft
                    # f0 = 4.50+0.99 # Initial coupler frequency in GH.z
                    # ft = fq+reset_amplitude# Final coupler frequency in GJ+Hz
                    # g = 0.071  # = coupling strength
                    # duration = (reset_duration)*1e9  # Pulse duration in nanosecond
                    
                    # sweep g, ft
                    # f0 = 4.50+0.935 # Initial coupler frequency in GHz
                    # ft = fq+reset_amplitude# Final coupler frequency in GJ+Hz
                    # g = reset_duration  # = coupling strength
                    # duration = 40  # Pulse duration in nanosecond

                    # fixed qc
                    # f0 = 4.50+0.93 # Initial coupler frequency in GHz
                    # ft = fq-0.2# Final coupler frequency in GJ+Hz
                    # g = 0.0290  # = coupling strength
                    # duration = 9  # Pulse duration in nanosecond

                    # f0 = 4.50+0.933 # Initial coupler frequency in GHz
                    # ft = fq-0.233# Final coupler frequency in GJ+Hz
                    # g = 0.05  # = coupling strength
                    # duration = 9  # Pulse duration in nanosecond

########################################################################################################################################################
                    # q22_q23
                    # sweep f0, t
                    # f0 = fq+reset_amplitude# Initial coupler frequency in GHz
                    # ft = fq-0.2 # Final coupler frequency in GJ+Hz
                    # g = 0.04  # = coupling strength
                    # duration = (reset_duration)*1e9  # Pulse duration in nanosecond

                    # sweep g, ft
                    # f0 = fq+0.635 # Ini1tial coupler frequency in GHz
                    # ft = fq+reset_amplitude# Final coupler frequency in GJ+Hz
                    # g = reset_duration  # = coupling strength
                    # duration = 8  # Pulse duration in nanosecond

                    f0 = fq+0.635 # Initial coupler frequency in GHz
                    ft = fq-0.256# Final coupler frequency in GJ+Hz
                    g = 0.01288  # = coupling strength
                    duration = 8  # Pulse duration in nanosecond

                    samples = generate_local_adiabatic_fc(g=g, duration=duration, f0=f0, ft=ft, fq=fq, dt=dt)
                    times = np.linspace(0, duration, int(np.ceil(duration / dt)))
                    samples[-2] = samples[-1]
                    qc = schedule.add(
                        NumericalPulse(
                            samples=samples,  # Numerical pulses can be complex as well.
                            t_samples=times*1e-9,
                            port = cz_pulse_port,
                            clock = cz_clock,
                        )
                    )
                    buffer = schedule.add(IdlePulse(4e-9),ref_op=buffer, ref_pt='end',rel_time = np.ceil( duration / 4) * 4e-9)
                    
                    # # sweep ft
                    # fq = 6.5 # qubit frequncy in GHz
                    # f0 = fq+0.5 # Initial coupler frequency in GHz
                    # ft = fq - reset_amplitude # Final coupler frequency in GJ+Hz
                    # g = 0.06  # = coupling strength
                    # duration = reset_duration*1e9  # Pulse duration in nanosecond
                    # dt = 1.0  # AWG sampling rate in nanosecond 

                    # sweep g,f0
                    # fq = 6.5 # qubit frequncy in GHz
                    # f0 = fq+reset_amplitude # Initial coupler frequency in GHz
                    # ft = fq - 1.0 # Final coupler frequency in GJ+Hz
                    # g = reset_duration  # = coupling strength
                    # duration = 7  # Pulse duration in nanosecond
                    # dt = 1.0  # AWG sampling rate in nanosecond 

                    # fixed cr
                    # fq = 6.5 # qubit frequncy in GHz
                    # f0 = fq + 1.45 # Initial coupler frequency in GHz
                    # ft = fq - 1.0 # Final coupler frequency in GJ+Hz
                    # g = 0.120  # = coupling strength
                    # duration = 7  # Pulse duration in nanosecond
                    # dt = 1.0  # AWG sampling rate in nanosecond 


                    # samples = generate_local_adiabatic_fc(g=g, duration=duration, f0=f0, ft=ft, fq=fq, dt=dt)
                    # times = np.linspace(0, duration, int(np.ceil(duration / dt)))
                    # samples[-2] = samples[-1]
                    # samples = samples + max(abs(samples))
                    # cr = schedule.add(
                    #     NumericalPulse(
                    #         samples=samples,  # Numerical pulses can be complex as well.
                    #         t_samples=times*1e-9,
                    #         port = cz_pulse_port,
                    #         clock = cz_clock,
                    #     )
                    # )
                    # buffer = schedule.add(IdlePulse(4e-9),ref_op=buffer, ref_pt='end',rel_time = np.ceil( duration / 4) * 4e-9)
                    
                    # cr = schedule.add(
                    #             RampPulse(
                    #                 offset = reset_amplitude,
                    #                 duration = reset_duration,
                    #                 amp = 0,
                    #                 # amp = 0.,
                    #                 port = cz_pulse_port,
                    #                 clock = cz_clock,
                    #             ),
                    #         )
                    # buffer = schedule.add(IdlePulse(4e-9),ref_op=buffer, ref_pt='end',rel_time = np.ceil( reset_duration * 1e9 / 4) * 4e-9)


                    # reset_amplitude_qc = -0.084
                    # reset_duration_qc = 16e-9
                    # qc = schedule.add(
                    #             RampPulse(
                    #                 offset = reset_amplitude_qc,
                    #                 duration = reset_duration_qc,
                    #                 amp = 0,
                    #                 # amp = 0.,
                    #                 port = cz_pulse_port,
                    #                 clock = cz_clock,
                    #             ),
                    #         )

                    # # qc = schedule.add(
                    # #             RampPulse(
                    # #                 offset = reset_amplitude,
                    # #                 duration = reset_duration,
                    # #                 amp = 0,
                    # #                 # amp = 0.,
                    # #                 port = cz_pulse_port,
                    # #                 clock = cz_clock,
                    # #             ),
                    # #         )
                    # buffer = schedule.add(IdlePulse(4e-9),ref_op=buffer, ref_pt='end',rel_time = np.ceil( reset_duration_qc * 1e9 / 4) * 4e-9)
                
                buffer_end = schedule.add(IdlePulse(4e-9))
                
                for this_qubit in qubits:
                    schedule.add(
                        Measure(this_qubit, acq_index=this_index, bin_mode=BinMode.AVERAGE),
                        ref_op=buffer_end, ref_pt="end",
                    )

        return schedule

class Reset_chevron_ac(Measurement):
    # for testing reset

    def __init__(self,transmons,coupler,qubit_state:int=0):
        super().__init__(transmons)
        self.qubit_state = qubit_state
        self.coupler = coupler
        self.static_kwargs = {
            'coupler': self.coupler,
            # 'mw_frequencies': self.attributes_dictionary('f01'),
            # 'mw_pulse_durations': self.attributes_dictionary('duration'),
            # 'mw_pulse_ports': self.attributes_dictionary('microwave'),
            # 'mw_ef_amps180': self.attributes_dictionary('ef_amp180'),
            # 'mw_frequencies_12': self.attributes_dictionary('f12'),
            #TODO temporarily comment out as they are hardcoded in the schedule
            #'cz_pulse_duration': self.attributes_dictionary('cz_pulse_duration'),
            #'cz_pulse_width': self.attributes_dictionary('cz_pulse_width'),
        }

    def schedule_function(
            self,
            coupler: str,
            cz_pulse_frequencies_sweep: dict[str,np.ndarray],
            cz_pulse_durations: dict[str,np.ndarray],
            cz_pulse_amplitude: float = 0.5,
            repetitions: int = 1024,
        ) -> Schedule:

        """
        Generate a schedule for performing a Ramsey fringe measurement on multiple qubits.
        Can be used both to finetune the qubit frequency and to measure the qubit dephasing time T_2. (1D parameter sweep)

        Schedule sequence
            Reset -> pi/2-pulse -> Idle(tau) -> pi/2-pulse -> Measure

        Parameters
        ----------
        self
            Contains all qubit states.
        qubits
            A list of two qubits to perform the experiment on. i.e. [['q1','q2'],['q3','q4'],...]
        mw_clocks_12
            Clocks for the 12 transition frequency of the qubits.
        mw_ef_amps180
            Amplitudes used for the excitation of the qubits to calibrate for the 12 transition.
        mw_frequencies_12
            Frequencies used for the excitation of the qubits to calibrate for the 12 transition.
        mw_pulse_ports
            Location on the device where the pulsed used for excitation of the qubits to calibrate for the 12 transition is located.
        mw_pulse_durations
            Pulse durations used for the excitation of the qubits to calibrate for the 12 transition.
        cz_pulse_frequency
            The frequency of the CZ pulse.
        cz_pulse_amplitude
            The amplitude of the CZ pulse.
        cz_pulse_duration
            The duration of the CZ pulse.
        cz_pulse_width
            The width of the CZ pulse.
        testing_group
            The edge group to be tested. 0 means all edges.
        repetitions
            The amount of times the Schedule will be repeated.

        Returns
        -------
        :
            An experiment schedule.
        """
        schedule = Schedule("CZ_chevron",repetitions)
        qubits = coupler.split(sep='_')

        cz_frequency_values = np.array(list(cz_pulse_frequencies_sweep.values())[0])
        cz_duration_values = list(cz_pulse_durations.values())[0]

        # print(f'{ cz_frequency_values[0] = }')
        couplers_list = [coupler]
        # find cz parameters from redis
        redis_connection = redis.Redis(decode_responses=True)
        cz_pulse_amplitude = {}
        for this_coupler in couplers_list:
            qubits = this_coupler.split(sep='_')
            cz_amplitude_values = []
            for qubit in qubits: 
                redis_config = redis_connection.hgetall(f"transmons:{qubit}")
                cz_amplitude_values.append(float(redis_config['cz_pulse_amplitude']))
            cz_pulse_amplitude[this_coupler] = cz_amplitude_values[0]
        print(f'{cz_pulse_amplitude = }')

        schedule.add_resource(
            ClockResource(name=coupler+'.cz',freq= - cz_frequency_values[0] + 4.4e9)
        )

        number_of_durations = len(cz_duration_values)

        # The outer loop, iterates over all cz_frequencies
        for freq_index, cz_frequency in enumerate(cz_frequency_values):
            cz_clock = f'{coupler}.cz'
            cz_pulse_port = f'{coupler}:fl'
            schedule.add(
                SetClockFrequency(clock=cz_clock, clock_freq_new= - cz_frequency + 4.4e9),
            )
            # schedule.add(
            #     SetClockFrequency(clock=cz_clock, clock_freq_new=4.4e9),
            # )

            #The inner for loop iterates over cz pulse durations
            for acq_index, cz_duration in enumerate(cz_duration_values):
                this_index = freq_index * number_of_durations + acq_index

                relaxation = schedule.add(Reset(*qubits))

                for this_qubit in qubits:
                    # schedule.add(X(this_qubit), ref_op=relaxation, ref_pt='end')
                    if this_qubit == 'q15':
                        schedule.add(X(this_qubit), ref_op=relaxation, ref_pt='end')
                        schedule.add(Rxy_12(this_qubit))
                    else:
                        schedule.add(IdlePulse(40e-9))
                        # schedule.add(X(this_qubit), ref_op=relaxation, ref_pt='end')
                        # schedule.add(Rxy_12(this_qubit))

                # cz_amplitude = 0.5
                buffer = schedule.add(IdlePulse(12e-9))

                cz = schedule.add(
                        SoftSquarePulse(
                            duration=cz_duration,
                            amp = cz_pulse_amplitude[this_coupler],
                            port=cz_pulse_port,
                            clock=cz_clock,
                        ),
                    )
                
                # reset test
                buffer = schedule.add(IdlePulse(cz_duration_values[-1]-cz_duration))
                # if this_qubit == 'q15':
                    # schedule.add(X90(this_qubit), ref_op=buffer, ref_pt='end')
                    # schedule.add(Rxy_12(this_qubit))
                # else:
                #     schedule.add(IdlePulse(20e-9))

                buffer = schedule.add(IdlePulse(12e-9))

                for this_qubit in qubits:
                    schedule.add(
                        Measure(this_qubit, acq_index=this_index, bin_mode=BinMode.AVERAGE),
                        ref_op=cz,rel_time=12e-9, ref_pt="end",
                    )
        return schedule


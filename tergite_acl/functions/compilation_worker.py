'''
Given the requested node
fetch and compile the appropriate schedule
'''
import json
from math import isnan

import numpy as np
from quantify_core.data.handling import set_datadir
from quantify_scheduler.backends import SerialCompiler
from quantify_scheduler.device_under_test.quantum_device import QuantumDevice

from tergite_acl.config.settings import HARDWARE_CONFIG, REDIS_CONNECTION
from tergite_acl.utils.extended_coupler_edge import CompositeSquareEdge
from tergite_acl.utils.extended_transmon_element import ExtendedTransmon
from tergite_acl.utils.logger.tac_logger import logger

set_datadir('../workers')

with open(HARDWARE_CONFIG) as hw:
    hw_config = json.load(hw)


def load_redis_config(transmon: ExtendedTransmon, channel: int):
    qubit = transmon.name
    redis_config = REDIS_CONNECTION.hgetall(f"transmons:{qubit}")
    transmon.reset.duration(float(redis_config['init_duration']))
    transmon.rxy.amp180(float(redis_config['mw_amp180']))
    transmon.r12.ef_amp180(float(redis_config['mw_ef_amp180']))
    motzoi_val = float(redis_config['mw_motzoi'])
    if isnan(motzoi_val):
        motzoi_val = 0
    transmon.rxy.motzoi(motzoi_val)
    transmon.rxy.duration(float(redis_config['mw_pulse_duration']))

    if not np.isnan(float(redis_config['spec_ampl_optimal'])):
        transmon.spec.spec_amp(float(redis_config['spec_ampl_optimal']))
    else:
        transmon.spec.spec_amp(float(redis_config['spec_ampl_default']))

    transmon.spec.spec_duration(float(redis_config['spec_pulse_duration']))
    # transmon.ports.microwave(redis_config['mw_port'])
    # transmon.ports.readout(redis_config['ro_port'])
    transmon.clock_freqs.f01(float(redis_config['freq_01']))
    transmon.clock_freqs.f12(float(redis_config['freq_12']))
    transmon.clock_freqs.readout(float(redis_config['ro_freq']))
    transmon.extended_clock_freqs.readout_1(float(redis_config['ro_freq_1']))
    transmon.extended_clock_freqs.readout_2(float(redis_config['ro_freq_2']))
    transmon.extended_clock_freqs.readout_opt(float(redis_config['ro_freq_2st_opt']))
    transmon.extended_clock_freqs.readout_3state_opt(float(redis_config['ro_freq_3st_opt']))
    ro_amp_opt = float(redis_config['ro_ampl_2st_opt'])
    if isnan(ro_amp_opt):
        ro_amp_opt = float(redis_config['ro_pulse_amp'])
    transmon.measure.pulse_amp(float(redis_config['ro_pulse_amp']))
    transmon.measure.pulse_duration(float(redis_config['ro_pulse_duration']))
    transmon.measure.acq_channel(channel)
    transmon.measure.acq_delay(float(redis_config['ro_acq_delay']))
    transmon.measure.integration_time(float(redis_config['ro_acq_integration_time']))
    transmon.measure_1.pulse_amp(float(redis_config['ro_pulse_amp']))
    transmon.measure_1.pulse_duration(float(redis_config['ro_pulse_duration']))
    transmon.measure_1.acq_channel(channel)
    transmon.measure_1.acq_delay(float(redis_config['ro_acq_delay']))
    transmon.measure_1.integration_time(float(redis_config['ro_acq_integration_time']))
    # transmon.measure_opt.pulse_amp(ro_amp_opt)
    transmon.measure_opt.pulse_duration(float(redis_config['ro_pulse_duration']))
    transmon.measure_opt.acq_channel(channel)
    transmon.measure_opt.acq_delay(float(redis_config['ro_acq_delay']))
    transmon.measure_opt.integration_time(float(redis_config['ro_acq_integration_time']))

    return


def load_redis_config_coupler(coupler: CompositeSquareEdge):
    bus = coupler.name
    redis_config = REDIS_CONNECTION.hgetall(f"couplers:{bus}")
    coupler.cz.cz_freq(float(redis_config['cz_pulse_frequency']))
    coupler.cz.square_amp(float(redis_config['cz_pulse_amplitude']))
    coupler.cz.square_duration(float(redis_config['cz_pulse_duration']))
    coupler.cz.cz_width(float(redis_config['cz_pulse_width']))
    return


def precompile(node, bin_mode: str = None, repetitions: int = None):
    # TODO: This has to be definitely handled by different classes
    # TODO: As soon as we have a tof class, all these if statements disappear
    if node.name == 'tof':
        return None, 1
    samplespace = node.samplespace
    qubits = node.all_qubits

    # TODO: This could be either a function for each different node class or a
    # backup old parameter values
    if node.backup:
        fields = node.redis_field
        for field in fields:
            field_backup = field + "_backup"
            for qubit in qubits:
                key = f"transmons:{qubit}"
                if field in REDIS_CONNECTION.hgetall(key).keys():
                    value = REDIS_CONNECTION.hget(key, field)
                    REDIS_CONNECTION.hset(key, field_backup, value)
                    REDIS_CONNECTION.hset(key, field, 'nan')
            if getattr(node, "coupler", None) is not None:
                couplers = node.coupler
                for coupler in couplers:
                    key = f"couplers:{coupler}"
                    if field in REDIS_CONNECTION.hgetall(key).keys():
                        value = REDIS_CONNECTION.hget(key, field)
                        REDIS_CONNECTION.hset(key, field_backup, value)
                        REDIS_CONNECTION.hset(key, field, 'nan')

    # TODO: This is hardcoded and we should move it to the .env file
    device = QuantumDevice(f'Loki_{node.name}')
    device.hardware_config(hw_config)

    transmons = {}
    for channel, qubit in enumerate(qubits):
        transmon = ExtendedTransmon(qubit)
        load_redis_config(transmon, channel)
        device.add_element(transmon)
        transmons[qubit] = transmon

    # Creating coupler edge
    # bus_list = [ [qubits[i],qubits[i+1]] for i in range(len(qubits)-1) ]
    # TODO: It seems like the coupler node is completely different to all other nodes
    if hasattr(node, 'couplers'):
        couplers = node.couplers
        edges = {}
        for bus in couplers:
            control, target = bus.split(sep='_')
            coupler = CompositeSquareEdge(control, target)
            load_redis_config_coupler(coupler)
            device.add_edge(coupler)
            edges[bus] = coupler

    # if node.name in ['cz_chevron','cz_calibration','cz_calibration_ssro','cz_dynamic_phase','reset_chevron']:
    if hasattr(node, 'edges'):
        coupler = node.coupler
        node_class = node.measurement_obj(transmons, edges, node.qubit_state)
    else:
        node_class = node.measurement_obj(transmons, node.qubit_state)
    if node.name in ['ro_amplitude_three_state_optimization', 'cz_calibration_ssro']:
        device.cfg_sched_repetitions(1)  # for single-shot readout
    if bin_mode is not None: node_class.set_bin_mode(bin_mode)

    schedule_function = node_class.schedule_function

    # Merge with the parameters from node dictionary
    static_parameters = node_class.static_kwargs  # parameters stored in the redis

    if repetitions is not None:
        static_parameters["repetitions"] = repetitions
    else:
        repetitions = 2**10
    node.demod_channels.set_repetitions(repetitions)

    for key, value in node.node_dictionary.items():
        if key in static_parameters:
            if not np.iterable(value):
                value = {q: value for q in qubits}
            static_parameters[key] = value
        elif key in samplespace:
            if not isinstance(value, dict):
                value = {q: value for q in qubits}
            samplespace[key] = value
        elif key != "couplers":
            static_parameters[key] = value
            # print(f"{key} isn't one of the static parameters of {node_class}. \n We will ignore this parameter.")

    if node.type == 'parameterized_sweep':
        external_parameters = {node.external_parameter_name: node.external_parameter_value}
    else:
        external_parameters = {}

    compiler = SerialCompiler(name=f'{node.name}_compiler')
    schedule = schedule_function(**static_parameters, **external_parameters, **samplespace)
    compilation_config = device.generate_compilation_config()
    device.close()

    # after the compilation_config is acquired, free the transmon resources
    for extended_transmon in transmons.values():
        extended_transmon.close()
    if hasattr(node, 'couplers'):
        for extended_edge in edges.values():
            extended_edge.close()

    logger.info('Starting Compiling')

    compiled_schedule = compiler.compile(schedule=schedule, config=compilation_config)

    # if node.name not in ['ro_amplitude_optimization_gef','cz_calibration_ssro']:
    #     try:
    #         figs = compiled_schedule.plot_pulse_diagram(plot_backend="plotly")
    #         figs.write_image(f'pulse_diagrams\{node.name}.png')
    #     except:
    #         pass
    # breakpoint()
    # figs[0].savefig('ssro')
    # breakpoint()

    # TODO
    # ic.retrieve_hardware_logs

    # with open(f'TIMING_TABLE_{node.name}.html', 'w') as file:
    #    file.write(
    #        compiled_schedule.timing_table.hide(['is_acquisition','wf_idx'],axis="columns"
    #            ).to_html()
    #        )

    return compiled_schedule

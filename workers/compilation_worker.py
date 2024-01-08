'''
Given the requested node
fetch and compile the appropriate schedule
'''
from logger.tac_logger import logger
from math import isnan
from quantify_scheduler.device_under_test.quantum_device import QuantumDevice
import redis
import json
import numpy as np
from utilities.extended_transmon_element import ExtendedTransmon
from utilities.extended_coupler_edge import CompositeSquareEdge
from quantify_scheduler.backends import SerialCompiler
from config_files.settings import hw_config_json
from quantify_core.data.handling import set_datadir

set_datadir('.')

with open(hw_config_json) as hw:
    hw_config = json.load(hw)

redis_connection = redis.Redis(decode_responses=True)

def load_redis_config(transmon: ExtendedTransmon, channel:int):
    qubit = transmon.name
    redis_config = redis_connection.hgetall(f"transmons:{qubit}")
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
    transmon.extended_clock_freqs.readout_opt(float(redis_config['ro_freq_opt']))
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

    transmon.measure_opt.pulse_amp(float(redis_config['ro_pulse_amp']))
    transmon.measure_opt.pulse_duration(float(redis_config['ro_pulse_duration']))
    transmon.measure_opt.acq_channel(channel)
    transmon.measure_opt.acq_delay(float(redis_config['ro_acq_delay']))
    transmon.measure_opt.integration_time(float(redis_config['ro_acq_integration_time']))
    return

def load_redis_config_coupler(coupler: CompositeSquareEdge):
    bus = coupler.name
    redis_config = redis_connection.hgetall(f"couplers:{bus}")
    coupler.cz.cz_freq(float(redis_config['cz_pulse_frequency']))
    coupler.cz.square_amp(float(redis_config['cz_pulse_amplitude']))
    coupler.cz.square_duration(float(redis_config['cz_pulse_duration']))
    coupler.cz.cz_width(float(redis_config['cz_pulse_width']))
    return

def precompile(node, bin_mode:str=None, repetitions:int=None):
    if node.name == 'tof':
        return None, 1
    samplespace = node.samplespace
    qubits = node.all_qubits

    # backup old parameter values
    if node.backup:
        fields = node.redis_field
        for field in fields:
            field_backup = field + "_backup"
            for qubit in qubits:
                key = f"transmons:{qubit}"
                if field in redis_connection.hgetall(key).keys():
                    value = redis_connection.hget(key, field)
                    redis_connection.hset(key, field_backup, value)
                    redis_connection.hset(key, field, 'nan' )
            if getattr(node, "coupler", None) is not None:
                couplers = node.coupler
                for coupler in couplers:
                    key = f"couplers:{coupler}"
                    if field in redis_connection.hgetall(key).keys():
                        value = redis_connection.hget(key, field)
                        redis_connection.hset(key, field_backup, value)
                        redis_connection.hset(key, field, 'nan')

    # TODO better way to restart the QuantumDevice object
    device = QuantumDevice(f'Loki_{node.name}')
    device.hardware_config(hw_config)
    sweep_parameters = list(samplespace.values())

    transmons = {}
    for channel, qubit in enumerate(qubits):
        transmon = ExtendedTransmon(qubit)
        load_redis_config(transmon,channel)
        device.add_element(transmon)
        transmons[qubit] = transmon

    # Creating coupler edge
    #bus_list = [ [qubits[i],qubits[i+1]] for i in range(len(qubits)-1) ]
    #couplers={}
    #for bus in bus_list:
    #    coupler = CompositeSquareEdge(bus[0],bus[1])
    #    load_redis_config_coupler(coupler)
    #    device.add_edge(coupler)
    #    couplers[bus[0]+'_'+bus[1]] = coupler

    node_class = node.measurement_obj(transmons, node.qubit_state)
    if node.name == 'cz_chevron':
        coupler = node.coupler
        node_class = node.measurement_obj(transmons, coupler, node.qubit_state)
    if bin_mode is not None: node_class.set_bin_mode(bin_mode)
    schedule_function = node_class.schedule_function

    # Merge with the parameters from node dictionary
    static_parameters = node_class.static_kwargs # parameters stored in the redis

    if repetitions is not None:
        static_parameters["repetitions"] = repetitions

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
            print(f"{key} isn't one of the static parameters of {node_class}. \n We will ignore this parameter.")

    # TODO commenting this out because single shots has been fixed by Qblox
    # _____________________________________________________________________
    # if 'qubit_states' in samplespace: #this means we have single shots
    #     shots = 1
    #     for subspace in samplespace.values():
    #         shots *= len( list(subspace.values())[0] )
    #     INSTRUCTIONS_PER_SHOT = 12
    #     QRM_instructions = 12200
    #
    #     def pairwise(iterable):
    #         #TODO after python 3.10 this will be replaced by itertools.pairwise
    #         # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    #         a, b = tee(iterable)
    #         next(b, None)
    #         return zip(a, b)
    #
    #     if len(samplespace) == 2:
    #         compiled_schedules = []
    #         schedule_durations = []
    #         samplespaces = []
    #         for coord, subspace in samplespace.items():
    #             if coord == 'qubit_states':
    #                 inner_dimension = len(list(subspace.values())[0])
    #             if coord != 'qubit_states':
    #                 outer_coordinate = coord
    #                 outer_dimension = len(list(subspace.values())[0])
    #         outer_batch = int(QRM_instructions/inner_dimension /INSTRUCTIONS_PER_SHOT)
    #         # make a partion like: [0,2,2,2,2]:
    #         outer_partition = [0] + [outer_batch] * (outer_dimension // outer_batch)
    #         # add the leftover partition: [0,2,2,2,2,0]:
    #         outer_partition += [outer_dimension % outer_batch]
    #         # take the cumulative sum: [0,2,4,6,8,8]
    #         # and with set() discard duplicates {0,2,4,6,8} then make a list:
    #         outer_partition = list(set(np.cumsum(outer_partition)))
    #         inner_samplespace = samplespace['qubit_states']
    #         slicing = list(pairwise(outer_partition))
    #         for slice_indx, slice_ in enumerate(slicing):
    #             partial_samplespace = {}
    #             partial_samplespace['qubit_states'] = inner_samplespace
    #             # we need to initialize every time, dict is mutable!!
    #             partial_samplespace[outer_coordinate] = {}
    #             for qubit, outer_samples in samplespace[outer_coordinate].items():
    #                 this_slice = slice(*slice_)
    #                 partial_samples = np.array(outer_samples)[this_slice]
    #                 partial_samplespace[outer_coordinate][qubit] = partial_samples
    #             schedule = schedule_function(**static_parameters,**partial_samplespace)
    #             logger.info(f'Starting Partial {slice_indx+1}/{len(list(slicing))} Compiling')
    #             #logger.info(f'Starting Partial Compiling')
    #             compilation_config = device.generate_compilation_config()
    #             compiled_schedule = compiler.compile(
    #                 schedule=schedule, config=compilation_config
    #             )
    #             logger.info('Finished Partial Compiling')
    #             compiled_schedules.append(compiled_schedule)
    #             schedule_durations.append(compiled_schedule.get_schedule_duration())
    #             samplespaces.append(partial_samplespace)
    #         return compiled_schedules, schedule_durations, samplespaces

    compiler = SerialCompiler(name=f'{node.name}_compiler')
    schedule = schedule_function(**static_parameters, **samplespace)
    compilation_config = device.generate_compilation_config()
    device.close()
    # after the compilation_config is acquired, free the transmon resources
    for extended_transmon in transmons.values():
        extended_transmon.close()
    #for extended_edge in couplers.values():
    #    extended_edge.close()

    logger.info('Starting Compiling')
    compiled_schedule = compiler.compile(schedule=schedule, config=compilation_config)

    logger.info('Finished Compiling')
    
    #TODO
    #ic.retrieve_hardware_logs
    # with open(f'TIMING_TABLE_{node}.html', 'w') as file:
    #    file.write(
    #        compiled_schedule.timing_table.hide(['is_acquisition','wf_idx'],axis="columns"
    #            ).to_html()
    #        )

    return compiled_schedule

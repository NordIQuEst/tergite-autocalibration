'''
Given the requested node
fetch and compile the appropriate schedule
'''

from quantify_scheduler.json_utils import SchedulerJSONDecoder, SchedulerJSONEncoder
from tergite_acl.lib.node_base import BaseNode
from tergite_acl.utils import extended_transmon_element
from tergite_acl.utils.logger.tac_logger import logger
from math import isnan
from quantify_scheduler.device_under_test.quantum_device import QuantumDevice
import redis
import json
import numpy as np
from tergite_acl.utils.extended_transmon_element import ExtendedTransmon
from tergite_acl.utils.extended_coupler_edge import CompositeSquareEdge
from quantify_scheduler.backends import SerialCompiler
from tergite_acl.config.settings import HARDWARE_CONFIG, REDIS_CONNECTION
from quantify_core.data.handling import set_datadir

set_datadir('.')

with open(HARDWARE_CONFIG) as hw:
    hw_config = json.load(hw)

redis_connection = redis.Redis(decode_responses=True)


def load_redis_config(transmon: ExtendedTransmon, channel:int):
    qubit = transmon.name
    redis_config = redis_connection.hgetall(f"transmons:{qubit}")

    # get the transmon template in dictionary form
    serialized_transmon = json.dumps(transmon, cls=SchedulerJSONEncoder)
    decoded_transmon = json.loads(serialized_transmon)

    # the transmon modules are recognized by the ':' in the redis key
    transmon_redis_config = {k:v for k,v in redis_config.items() if ':' in k}
    device_redis_dict = {}
    for redis_entry_key, redis_value in transmon_redis_config.items():
        redis_value = float(redis_value)
        # e.g. 'clock_freqs:f01' is split to clock_freqs, f01
        submodule, field = redis_entry_key.split(':')
        device_redis_dict[submodule] = device_redis_dict.get(submodule, {}) | {field: redis_value}

    device_redis_dict['name'] = qubit

    for submodule in decoded_transmon['data']:
        sub_module_content = decoded_transmon['data'][submodule]
        # update the dictionary of each module of the serialized extended transmon
        # with the corresponding module dictionary from redis
        if isinstance(sub_module_content, dict) and submodule in device_redis_dict:
            redis_module_config = device_redis_dict[submodule]
            decoded_transmon['data'][submodule].update(redis_module_config)
        if 'measure' in submodule:
            decoded_transmon['data'][submodule].update({'acq_channel': channel})

    encoded_transmon = json.dumps(decoded_transmon)

    # free the transmon
    transmon.close()

    # create a transmon with the same name but with updated config
    transmon = json.loads(
        encoded_transmon,
        cls=SchedulerJSONDecoder,
        modules=[extended_transmon_element]
    )

    return transmon


def load_redis_config_coupler(coupler: CompositeSquareEdge):
    bus = coupler.name
    redis_config = redis_connection.hgetall(f"couplers:{bus}")
    coupler.cz.cz_freq(float(redis_config['cz_pulse_frequency']))
    coupler.cz.square_amp(float(redis_config['cz_pulse_amplitude']))
    coupler.cz.square_duration(float(redis_config['cz_pulse_duration']))
    coupler.cz.cz_width(float(redis_config['cz_pulse_width']))
    return

def precompile(node: BaseNode, bin_mode:str=None, repetitions:int=None):
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

    device = QuantumDevice(f'Loki_{node.name}')
    device.hardware_config(hw_config)

    transmons = {}
    for channel, qubit in enumerate(qubits):
        transmon = ExtendedTransmon(qubit)
        transmon = load_redis_config(transmon,channel)
        device.add_element(transmon)
        transmons[qubit] = transmon

    # Creating coupler edge
    #bus_list = [ [qubits[i],qubits[i+1]] for i in range(len(qubits)-1) ]
    if hasattr(node, 'edges'):
        couplers = node.edges
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
    if node.name in ['ro_amplitude_three_state_optimization','cz_calibration_ssro']:
        device.cfg_sched_repetitions(1)    # for single-shot readout
    if bin_mode is not None: node_class.set_bin_mode(bin_mode)

    schedule_function = node_class.schedule_function

    if repetitions is not None:
        static_parameters["repetitions"] = repetitions
    else:
        repetitions = 2**10
    node.demod_channels.set_repetitions(repetitions)

    # for key, value in node.node_dictionary.items():
    #     if key in static_parameters:
    #         if not np.iterable(value):
    #             value = {q: value for q in qubits}
    #         static_parameters[key] = value
    #     elif key in samplespace:
    #         if not isinstance(value, dict):
    #             value = {q: value for q in qubits}
    #         samplespace[key] = value
    #     elif key != "couplers":
    #         static_parameters[key] = value
    #         # print(f"{key} isn't one of the static parameters of {node_class}. \n We will ignore this parameter.")

    # if node.type == 'parameterized_sweep' or node.type == 'adaptive_sweep':
    #     external_parameters = {node.external_parameter_name: node.external_parameter_value}
    # else:
    #     external_parameters = {}

    compiler = SerialCompiler(name=f'{node.name}_compiler')

    schedule_samplespace = node.schedule_samplespace
    external_samplespace = node.external_samplespace

    samplespace = schedule_samplespace | external_samplespace

    schedule = schedule_function( **samplespace )
    compilation_config = device.generate_compilation_config()
    device.close()

    # after the compilation_config is acquired, free the transmon resources
    for extended_transmon in transmons.values():
        extended_transmon.close()
    if hasattr(node, 'edges'):
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

    #TODO
    # ic.retrieve_hardware_logs

    # with open(f'TIMING_TABLE_{node.name}.html', 'w') as file:
    #    file.write(
    #        compiled_schedule.timing_table.hide(['is_acquisition','wf_idx'],axis="columns"
    #            ).to_html()
    #        )

    return compiled_schedule

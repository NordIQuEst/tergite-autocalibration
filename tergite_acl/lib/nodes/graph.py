import networkx as nx
import matplotlib.pyplot as plt

graph = nx.DiGraph()

# dependencies: n1 -> n2. For example
# ('tof','resonator_spectroscopy')
# means 'resonator_spectroscopy' depends on 'tof'
import pathlib
from datetime import datetime
from uuid import uuid4

import numpy as np
import xarray

from tergite_acl.config.settings import DATA_DIR
from tergite_acl.lib.demod_channels import ParallelDemodChannels
from tergite_acl.lib.node_base import BaseNode

def configure_dataset(
        raw_ds: xarray.Dataset,
        node: BaseNode,
    ) -> xarray.Dataset:
    '''
    The dataset retrieved from the instrument coordinator is
    too bare-bones. Here the dims, coords and data_vars are configured
    '''
    dataset = xarray.Dataset()

    keys = raw_ds.data_vars.keys()
    measurement_qubits = node.all_qubits
    samplespace = node.samplespace

    sweep_quantities = samplespace.keys()

    n_qubits = len(measurement_qubits)

    for key in keys:
        key_indx = key%n_qubits # this is to handle ro_opt_frequencies node where
        # there are 2 or 3 measurements (i.e 2 or 3 Datarrays) for each qubit
        coords_dict = {}
        measured_qubit = measurement_qubits[key_indx]

        for quantity in sweep_quantities :

            # eg ['q1','q2',...] or ['q1_q2','q3_q4',...] :
            settable_elements = samplespace[quantity].keys()

            # distinguish if the settable is on a qubit or a coupler:
            if measured_qubit in settable_elements:
                element = measured_qubit
                element_type = 'qubit'
            else:
                matching = [s for s in settable_elements if measured_qubit in s]
                if len(matching) == 1 and '_' in matching[0]:
                    element = matching[0]
                    element_type = 'coupler'
                else:
                    raise(ValueError)

            coord_key = quantity + element
            settable_values = samplespace[quantity][element]
            coord_attrs = {
                'element_type': element_type, # 'element_type' is ether 'qubit' or 'coupler'
                element_type: element,
                'long_name': f'{coord_key}',
                'units': 'NA'
            }

            coords_dict[coord_key] = (coord_key, settable_values, coord_attrs)

        if hasattr(node, 'node_externals'):
            coord_key = node.external_parameter_name + measured_qubit
            coord_attrs = {'qubit':measured_qubit, 'long_name': f'{coord_key}', 'units': 'NA'}
            coords_dict[coord_key] = (coord_key, np.array([node.external_parameter_value]), coord_attrs)

        partial_ds = xarray.Dataset(coords=coords_dict)

        data_values = raw_ds[key].values

        if node.name == 'ro_amplitude_two_state_optimization' or node.name == 'ro_amplitude_three_state_optimization':
            loops = node.node_dictionary['loop_repetitions']
            for key in coords_dict.keys():
                if measured_qubit in key and 'ro_amplitudes' in key:
                    ampls = coords_dict[key][1]
                elif measured_qubit in key and 'qubit_states' in key:
                    states = coords_dict[key][1]
            data_values = reshufle_loop_dataset(data_values, ampls, states, loops)

        # TODO this is not safe:
        # This assumes that the inner settable variable is placed
        # at the first position in the samplespace
        reshaping = reversed(node.dimensions)
        data_values = data_values.reshape(*reshaping)
        data_values = np.transpose(data_values)
        attributes = {'qubit': measured_qubit, 'long_name': f'y{measured_qubit}', 'units': 'NA'}
        qubit_state = ''

        # TODO ro_frequency_optimization requires multiple measurements per qubit
        is_frequency_opt = node.name == 'ro_frequency_two_state_optimization' or node.name == 'ro_frequency_three_state_optimization'
        if is_frequency_opt:
            qubit_states = [0,1,2]
            qubit_state = qubit_states[key // n_qubits]
            attributes['qubit_state'] = qubit_state

        partial_ds[f'y{measured_qubit}{qubit_state}'] = (tuple(coords_dict.keys()), data_values, attributes)
        dataset = xarray.merge([dataset,partial_ds])

    return dataset



# def configure_dataset(
#         raw_ds: xarray.Dataset,
#         node: 'BaseNode',
#         ) -> xarray.Dataset:
#     '''The dataset retrieved from the instrument coordinator  is
#        too bare-bones. Here we configure the dims, coords and data_vars'''
#     samplespace = node.samplespace
#     # For multiplexed single-qubit readout, parallel_demod_channels
#     # are union of single DemodChannel. The channel label is the name
#     # of qubit.
#     parallel_demod_channels: ParallelDemodChannels = node.demod_channels
#
#     dataset = xarray.Dataset()
#     # The union of qubits which will be demodulated.
#     total_qubits = parallel_demod_channels.qubits_demod
#     n_qubits = len(total_qubits)
#
#     for demod_channel in parallel_demod_channels.demod_channels:
#         qubits = demod_channel.qubits # The qubits contained in this channel.
#         channel_label = demod_channel.channel_label # The name of the channel
#         coords_dict = {}
#         for quantity in samplespace:
#             # e.g., samplesapce[quantify] = {'q1': np.arange(0, 1, 0.1)}
#             if channel_label in samplespace[quantity]:
#                 settable_values = samplespace[quantity][channel_label]
#                 settable_elements = samplespace[quantity].keys()
#             else:
#                 settable_values = None
#
#             if settable_values is not None:
#                 if channel_label in settable_elements: # change the parameter of a qubit
#                     element = channel_label
#                     element_type = 'qubit'
#                 else:
#                     matching = [s for s in settable_elements if channel_label in s] # change the parameter of a coupler
#                     if len(matching) == 1 and '_' in matching[0]:
#                         element = matching[0]
#                         element_type = 'coupler'
#                     else:
#                         raise (ValueError)
#                 coord_key = quantity + element
#                 settable_values = samplespace[quantity][element]
#                 coord_attrs = {element_type: element, 'long_name': f'{coord_key}', 'units': 'NA'}
#                 coords_dict[coord_key] = (coord_key, settable_values, coord_attrs)
#
#                 if hasattr(node, 'node_externals'):
#                     coord_key = node.external_parameter_name + channel_label
#                     coord_attrs = {'qubit': channel_label, 'long_name': f'{coord_key}', 'units': 'NA'}
#                     coords_dict[coord_key] = (coord_key, np.array([node.external_parameter_value]), coord_attrs)
#
#         dimensions = [len(samplespace[quantity][channel_label]) if isinstance(samplespace[quantity], dict) else len(samplespace[quantity]) for quantity in samplespace]
#         reshaping = list(reversed(dimensions))
#         data_values_multiqubit = []
#         for qubit in qubits:
#             # The index of qubit to be demodulated stored as the key of data_vars in raw_ds
#             qubit_index = total_qubits.index(qubit)
#             data_values = raw_ds[qubit_index].values
#
#             if node.name == 'ro_amplitude_two_state_optimization' or node.name == 'ro_amplitude_three_state_optimization':
#                 loops = node.node_dictionary['loop_repetitions']
#                 for key in coords_dict.keys():
#                     if channel_label in key and 'ro_amplitudes' in key:
#                         ampls = coords_dict[key][1]
#                     elif channel_label in key and 'qubit_states' in key:
#                         states = coords_dict[key][1]
#                 data_values = reshufle_loop_dataset(data_values, ampls, states, loops)
#
#             # Reshape the data_values
#             data_values_reshape = data_values.reshape(*reshaping)
#             data_values_multiqubit.append(data_values_reshape)
#         data_values_multiqubit = np.array(data_values_multiqubit)
#         # Adjust the order of dimension
#         data_values = tunneling_qubits(data_values_multiqubit)
#         if len(qubits) == 1:
#             # Single-qubit demodulation
#             attributes = {'qubit': qubits[0], 'long_name': f'y{qubit}', 'units': 'NA', 'channel_label': channel_label, 'repetitions':demod_channel.repetitions}
#         else:
#             # Multi-qubit demodulation
#             attributes = {'qubits': qubits, 'long_name': '_'.join([f'y{qubit}' for qubit in qubits]), 'units': 'NA', 'channel_label': channel_label, 'repetitions':demod_channel.repetitions}
#
#         # TODO ro_frequency_optimization requires multiple measurements per qubit
#         is_frequency_opt = node.name == 'ro_frequency_two_state_optimization' or node.name == 'ro_frequency_three_state_optimization'
#         if is_frequency_opt:
#             qubit_states = [0,1,2]
#             qubit_state = qubit_states[key // n_qubits]
#             attributes['qubit_state'] = qubit_state
#
#         partial_ds = xarray.Dataset(coords=coords_dict)
#         partial_ds[f'y{channel_label}'] = (tuple(coords_dict.keys()), data_values, attributes)
#         dataset = xarray.merge([dataset,partial_ds])
#     return dataset

def to_real_dataset(iq_dataset: xarray.Dataset) -> xarray.Dataset:
    ds = iq_dataset.expand_dims('ReIm', axis=-1)  # Add ReIm axis at the end
    ds = xarray.concat([ds.real, ds.imag], dim='ReIm')
    return ds


def reshufle_loop_dataset(
    initial_array: np.ndarray, ampls, states, loops: int
    ):
    initial_shape = initial_array.shape
    initial_array = initial_array.flatten()
    states = np.unique(states)
    reshuffled_array = np.empty_like(initial_array)
    n_states = len(states)
    for i, el in enumerate(initial_array):
        measurements_per_loop = len(ampls) * n_states
        amplitude_group = (i % measurements_per_loop) // n_states
        new_index_group = amplitude_group * loops * n_states
        loop_number = i // measurements_per_loop
        new_index = new_index_group + loop_number * n_states + i % n_states
        reshuffled_array[new_index] = el
    reshuffled_array.reshape(*initial_shape)
    return reshuffled_array


def handle_ro_freq_optimization(complex_dataset: xarray.Dataset, states: list[int]) -> xarray.Dataset:
    new_ds = xarray.Dataset(coords=complex_dataset.coords, attrs=complex_dataset.attrs)
    new_ds = new_ds.expand_dims(dim={'qubit_state': states})
    # TODO this for every var and every coord. It might cause
    # performance issues for larger datasets
    for coord in complex_dataset.coords:
        this_qubit = complex_dataset[coord].attrs['qubit']
        attributes = {'qubit': this_qubit}
        values = []
        for var in complex_dataset.data_vars:
            if coord in complex_dataset[var].coords:
                values.append(complex_dataset[var].values)
        new_ds[f'y{this_qubit}'] = (('qubit_state', coord), np.vstack(values), attributes)
    return new_ds


def create_node_data_path(node):
    measurement_date = datetime.now()
    measurements_today = measurement_date.date().strftime('%Y%m%d')
    time_id = measurement_date.strftime('%Y%m%d-%H%M%S-%f')[:19]
    measurement_id = time_id + '-' + str(uuid4())[:6] + f'-{node.name}'
    data_path = pathlib.Path(DATA_DIR / measurements_today / measurement_id)
    return data_path


def retrieve_dummy_dataset(result_dataset: xarray.Dataset, node) -> xarray.Dataset:
    if node.name == 'resonator_spectroscopy':
        ds_path = 'tergite_acl/utils/dummy_datasets/20240312-092341-245-0c45cb-resonator_spectroscopy/dataset.hdf5'
    elif node.name == 'qubit_01_spectroscopy':
        ds_path = 'tergite_acl/utils/dummy_datasets/20240312-092355-781-934808-qubit_01_spectroscopy/dataset.hdf5'
    elif node.name == 'rabi_oscillations':
        ds_path = 'tergite_acl/utils/dummy_datasets/20240312-092445-965-2c64c2-rabi_oscillations/dataset.hdf5'
    elif node.name == 'ramsey_correction':
        ds_path = 'tergite_acl/utils/dummy_datasets/20240312-092539-970-23d58e-ramsey_correction/'
    else:
        raise ValueError('Node does not have a stored dummy dataset')

    real_dataset = xarray.open_dataset(ds_path)
    dummy_ds = real_dataset.isel(ReIm=0) + 1j * real_dataset.isel(ReIm=1)

    #TODO probably this is not needed for newer datasets
    for data_var in dummy_ds.data_vars:
        dummy_ds[data_var].attrs.update({'qubit': data_var[1:]})
    for coord in dummy_ds.coords:
        dummy_ds[coord].attrs.update({'element_type': 'qubit'})
    return dummy_ds



def save_dataset(result_dataset: xarray.Dataset, node, data_path: pathlib.Path):
    data_path.mkdir(parents=True, exist_ok=True)
    measurement_id = data_path.stem[0:19]
    result_dataset = result_dataset.assign_attrs({'name': node.name, 'tuid': measurement_id})
    result_dataset_real = to_real_dataset(result_dataset)
    # to_netcdf doesn't like complex numbers, convert to real/imag to save:
    result_dataset_real.to_netcdf(data_path / 'dataset.hdf5')

def tunneling_qubits(data_values:np.ndarray) -> np.ndarray:
    if data_values.shape[0] == 1:
        # Single-qubit demodulation
        data_values = data_values[0]
        dims = len(data_values.shape)
        # Transpose data_values
        return np.moveaxis(data_values, range(dims), range(dims-1, -1, -1))
    else:
        dims = len(data_values.shape)
        # Transpose data_values.
        # The first dimension corresponds to the index of qubits.
        return np.moveaxis(data_values, range(1, dims), range(dims-1, 0, -1))
graph_dependencies = [
    # _____________________________________
    # these are edges on  a directed graph
    # _____________________________________
    ('tof', 'resonator_spectroscopy'),
    # ('resonator_spectroscopy', 'coupler_resonator_spectroscopy'),
    # ('resonator_spectroscopy', 'qubit_01_spectroscopy_pulsed'),
    ('qubit_01_spectroscopy', 'coupler_spectroscopy'),
    ('resonator_spectroscopy', 'qubit_01_spectroscopy'),
    # ('qubit_01_spectroscopy_pulsed', 'rabi_oscillations'),
    ('qubit_01_spectroscopy', 'rabi_oscillations'),

    ('rabi_oscillations', 'ramsey_correction'),
    # ('ramsey_correction', 'adaptive_motzoi_parameter'),
    # ('rabi_oscillations', 'adaptive_ramsey_correction'),
    ('adaptive_ramsey_correction', 'adaptive_motzoi_parameter'),

    ('adaptive_motzoi_parameter', 'n_rabi_oscillations'),
    ('n_rabi_oscillations', 'resonator_spectroscopy_1'),
    ('randomized_benchmarking', 'T1'),
    ('n_rabi_oscillations', 'resonator_spectroscopy_1'),
    ('n_rabi_oscillations', 'all_XY'),
    # ('n_rabi_oscillations', 'T1'),
    ('n_rabi_oscillations', 'randomized_benchmarking'),
    ('resonator_spectroscopy_1', 'ro_frequency_two_state_optimization'),
    ('ro_frequency_two_state_optimization', 'ro_amplitude_two_state_optimization'),
    # ('randomized_benchmarking', 'T1'),
    ('T1', 'T2'),
    ('T2', 'T2_echo'),
    # ('T2_echo', 'ramsey_correction'),
    # ('resonator_spectroscopy_1', 'qubit_12_spectroscopy_pulsed'),
    ('resonator_spectroscopy_1', 'qubit_12_spectroscopy'),
    # ('qubit_12_spectroscopy_pulsed', 'rabi_oscillations_12'),
    # ('qubit_12_spectroscopy_multidim', 'cz_optimize_chevron'),
    ('qubit_12_spectroscopy', 'rabi_oscillations_12'),
    ('rabi_oscillations_12', 'ramsey_correction_12'),
    ('ramsey_correction_12', 'resonator_spectroscopy_2'),
    ('resonator_spectroscopy_2', 'ro_frequency_three_state_optimization'),
    ('ro_frequency_three_state_optimization', 'ro_amplitude_three_state_optimization'),
    # ('coupler_spectroscopy', 'cz_chevron'),
    ('ro_amplitude_three_state_optimization', 'cz_chevron'),
    # ('rabi_oscillations', 'reset_chevron'),
    # ('cz_chevron', 'cz_calibration'),
    # ('qubit_12_spectroscopy_multidim', 'cz_calibration'),
    # ('cz_calibration', 'cz_calibration_ssro'),
    # ('cz_calibration', 'cz_calibration_ssro'),
    # ('cz_calibration', 'cz_dynamic_phase')
]

graph.add_edges_from(graph_dependencies)
# For DEVELOPMENT PURPOSES the nodes that update an existing redis redis_field
# are given a refine attr so they can be skipped if desired
graph.add_node('tof', type='refine')
graph.add_node('punchout')
# graph.add_node('qubit_01_spectroscopy_pulsed')
graph.add_node('qubit_01_spectroscopy')
# graph.add_node('T1', type='refine')
# graph.add_node('T2', type='refine')
# graph.add_node('T2_echo', type='refine')
# graph.add_node('ramsey_correction', type='refine')
# graph.add_node('adaptive_motzoi_parameter', type='refine')
# graph.add_node('n_rabi_oscillations', type='refine')
# graph.add_node('ramsey_correction_12', type='refine')
# graph.add_node('ro_frequency_optimization_gef', type='refine')
# graph.add_node('ro_amplitude_optimization_gef', type='refine')
# graph.add_node('resonator_spectroscopy_2', type='refine')

# for nodes that perform the same measurement,
# assign a weight to the corresponding edge to sort them
# graph['resonator_spectroscopy']['qubit_01_spectroscopy_pulsed']['weight'] = 2
# graph['resonator_spectroscopy']['qubit_01_spectroscopy']['weight'] = 1
graph['resonator_spectroscopy_1']['qubit_12_spectroscopy']['weight'] = 2
graph['resonator_spectroscopy_1']['qubit_12_spectroscopy']['weight'] = 1

initial_pos = {
    'tof': (0,1),
    'resonator_spectroscopy': (0,0.9),
    'qubit_01_spectroscopy': ( 0.0,0.85),
    # 'qubit_01_spectroscopy_pulsed': (-0.5,0.8),
    'rabi_oscillations': (0,0.8),
    'ramsey_correction': (0,0.75),
    'adaptive_motzoi_parameter': (0.0,0.7),
    'n_rabi_oscillations': (0.0,0.65),
    'resonator_spectroscopy_1': (0,0.6),
    'ro_frequency_two_state_optimization': (-0.2,0.45),
    'ro_amplitude_two_state_optimization': (-0.2,0.35),
    # 'qubit_12_spectroscopy_pulsed': (-0.5,0.4),
    'qubit_12_spectroscopy': (0.0,0.55),
    'rabi_oscillations_12': (0,0.5),

    'ramsey_correction_12': (0,0.45),
    'resonator_spectroscopy_2': (0,0.4),
    'ro_frequency_three_state_optimization': (0.15,0.35),
    'ro_amplitude_three_state_optimization': (0.15,0.25),
    'cz_chevron': (0.0,0.2),
    'cz_calibration': (-0.9,0.0),
    'T1': (0.25,0.55),
    'T2': (0.35,0.55),
    'T2_echo': (0.5,0.55),
    'randomized_benchmarking': (0.45,0.4),
    'state_discrimination': (0.5,0.3),
    'coupler_spectroscopy': (0.3,0.7),
    'punchout': (0.3,0.9),
}


# all_nodes = list(nx.topological_sort(graph))
# print(f'{ list(graph.predecessors("cz_chevron")) = }')
# graph.remove_node('coupler_spectroscopy')
# print(f'{ list(graph.predecessors("cz_chevron")) = }')

# TODO add condition argument and explanation
def filtered_topological_order(target_node: str):
    target_ancestors = nx.ancestors(graph, target_node)
    if 'coupler_spectroscopy' in target_ancestors:
        coupler_path = nx.shortest_path(graph, 'resonator_spectroscopy', 'coupler_spectroscopy')
        graph.remove_node('coupler_spectroscopy')
    else:
        coupler_path = []

    if target_node == 'punchout':
        topo_order = ['punchout']
    else:
        topo_order = nx.shortest_path(
            graph, 'resonator_spectroscopy', target_node, weight='weight'
        )

    def graph_condition(node, types):
        is_without_type = 'type' not in graph.nodes[node]
        if is_without_type:
            return True
        has_correct_type = graph.nodes[node]['type'] in types
        return not is_without_type and has_correct_type

    filtered_order = [node for node in topo_order if graph_condition(node, 'refine')]
    filtered_order = coupler_path + filtered_order
    # print(f'{ filtered_order = }')
    # quit()
    return filtered_order


if __name__ == "__main__":
    # nx.draw_spring(graph, with_labels=True, k=1, pos = initial_pos)
    # pos = nx.spring_layout(graph, k=0.3)
    nx.draw(graph, with_labels=True, pos = initial_pos,node_color='#FDFD96', node_shape='o',node_size=500)
    # nx.draw(graph, pos=nx.spring_layout(graph, k=0.3), with_labels=True)
    plt.show()


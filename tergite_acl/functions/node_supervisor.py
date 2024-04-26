import xarray
from tergite_acl.utils.dataset_utils import retrieve_dummy_dataset
from tergite_acl.utils.status import ClusterStatus
from tergite_acl.functions.compilation_worker import precompile
from tergite_acl.functions.execution_worker import measure_node
from tergite_acl.utils.hardware_utils import SpiDAC
from tergite_acl.functions.post_processing_worker import post_process
from tergite_acl.utils.logger.tac_logger import logger
import scipy.optimize as optimize

'''
sweep types:
simple_sweep:
   sweep on a predefined samplespace on cluster-controlled parameters.
   The schedule is compiled only once.
   At the moment, most of nodes are of this type.

   If the length of the external_parameters is not zero,
   each external parameter is updated and the measurement is repeated.
   e.g. in the anticrossing measurement the DC current is the external
   parameter or in the T1 measurement, teh measurement repetition is the
   external parameter

parameterized_sweep:
    sweep under a schedule parameter e.g. RB.
    For every external parameter value, the schedule is recompiled.
adaptive_sweep:
    modify the samplespace after each sweep and repeat
    For every external parameter value, the schedule is recompiled.
'''

def monitor_node_calibration(node, data_path, lab_ic, cluster_status):
    if node.type == 'simple_sweep':
        compiled_schedule = precompile(node)

        if len(node.node_externals) == 0:
            '''
            This correspond to simple cluster schedules
            '''
            result_dataset = measure_node(
            node,
            compiled_schedule,
            lab_ic,
            data_path,
            cluster_status=cluster_status,
        )
        else:
            external_parameter_values = node.node_externals
            pre_measurement_operation = node.pre_measurement_operation
            operations_args = node.operations_args

            result_dataset = xarray.Dataset()

            for node_parameter in external_parameter_values:
                node.external_parameter_value = node_parameter
                pre_measurement_operation(*operations_args, external=node_parameter)
                ds = measure_node(
                    node,
                    compiled_schedule,
                    lab_ic,
                    data_path,
                    cluster_status,
                    measurement=(node_parameter, len(external_parameter_values))
                )
                result_dataset = xarray.merge([result_dataset, ds])

        logger.info('measurement completed')
        measurement_result = post_process(result_dataset, node, data_path=data_path)
        logger.info('analysis completed')


    elif node.type == 'parameterized_sweep':
        print('Performing parameterized sweep')
        ds = xarray.Dataset()

        iterations = len(node.node_externals)

        for iteration_index in range(node.external_iterations):
            if iteration_index == node.external_iterations:
                # TODO remove this, such attributes are not a responsibility of the node
                node.measurement_is_completed = True
            node_parameter = node.node_externals[iteration_index]
            node.external_parameter_value = node_parameter
            node.external_parameters = {
                node.external_parameter_name: node_parameter
            }
            # reduce the external samplespace
            compiled_schedule = precompile(node)

            result_dataset = measure_node(
                node,
                compiled_schedule,
                lab_ic,
                data_path,
                cluster_status,
            )

            if node.post_process_each_iteration:
                measurement_result = post_process(result_dataset, node, data_path=data_path)
            ds = xarray.merge([ds, result_dataset])

        logger.info('measurement completed')
        if not node.post_process_each_iteration:
            measurement_result = post_process(ds, node, data_path=data_path)
        logger.info('analysis completed')

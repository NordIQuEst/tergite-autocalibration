'''Retrieve the compiled schedule and run it'''
from datetime import datetime
from time import sleep
from uuid import uuid4
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
from qblox_instruments.ieee488_2 import DummyBinnedAcquisitionData
colorama_init()

from quantify_scheduler.instrument_coordinator.instrument_coordinator import CompiledSchedule
from logger.tac_logger import logger

from qblox_instruments import Cluster, ClusterType
from quantify_scheduler.instrument_coordinator import InstrumentCoordinator
from quantify_scheduler.instrument_coordinator.components.qblox import ClusterComponent
import xarray
from utilities.status import ClusterStatus
import numpy as np
import threading
import tqdm
from utilities.root_path import data_directory
from calibration_schedules.time_of_flight import measure_time_of_flight
from config_files.settings import lokiA_IP

import redis

redis_connection = redis.Redis(decode_responses=True)

def configure_dataset(
        raw_ds: xarray.Dataset,
        samplespace: dict[str, dict[str,np.ndarray]],
        ) -> xarray.Dataset:
    '''The dataset retrieved from the instrument coordinator  is
       too bare-bones. Here we configure the dims, coords and data_vars'''
    logger.info('Configuring Dataset')
    dataset = xarray.Dataset()
    keys = sorted(list(raw_ds.data_vars.keys()))
    sweep_quantities = samplespace.keys() # for example 'ro_frequencies', 'ro_amplitudes' ,...
    sweep_parameters = list(samplespace.values())[0]
    qubits = list(sweep_parameters.keys())


    for key in keys:
        # dim = f'{sweep_quantity}_{qubits[key]}'
        coords_dict = {}
        for quantity in sweep_quantities :
            coord_key = quantity+qubits[key]
            coords_dict[coord_key] = (coord_key, samplespace[quantity][qubits[key]])
        partial_ds = xarray.Dataset(coords=coords_dict)
        reshaping = list(reversed([len(samplespace[quantity][qubits[key]]) for quantity in sweep_quantities]))
        data_values = raw_ds[key].values[0].reshape(*reshaping)
        data_values = np.transpose(data_values)
        partial_ds[f'y{qubits[key]}_real'] = (tuple(coords_dict.keys()), data_values.real, {'qubit': qubits[key]})
        partial_ds[f'y{qubits[key]}_imag'] = (tuple(coords_dict.keys()), data_values.imag, {'qubit': qubits[key]})
        dataset = xarray.merge([dataset,partial_ds])
    return dataset

def to_complex_dataset(iq_dataset: xarray.Dataset) -> xarray.Dataset:
    dataset_dict = {}
    complex_ds = xarray.Dataset(coords=iq_dataset.coords)
    for var in iq_dataset.data_vars.keys():
        this_qubit = iq_dataset[var].attrs['qubit']
        #TODO this could be better:
        if not this_qubit in dataset_dict:
            dataset_dict[this_qubit] = {}
        current_values = iq_dataset[var].values
        if 'real' in var:
            dataset_dict[this_qubit]['real'] = current_values
        elif 'imag' in var:
            dataset_dict[this_qubit]['imag'] = current_values

        if 'real' in dataset_dict[this_qubit] and 'imag' in dataset_dict[this_qubit]:
            qubit_coords = iq_dataset[f'y{this_qubit}_real'].coords
            complex_values = dataset_dict[this_qubit]['real'] + 1j*dataset_dict[this_qubit]['imag']
            complex_ds[f'y{this_qubit}'] = (qubit_coords, complex_values, {'qubit': this_qubit})

    return complex_ds

def measure( compiled_schedule: CompiledSchedule, schedule_duration: float, samplespace: dict, node: str) -> xarray.Dataset:
    cluster_status = ClusterStatus.dummy

    logger.info('Starting measurement')

    #Runs time of flight calibration
    #TODO this is a very bad way of running TOF
    # ideally TOF would be its own node, but this requires custom input variables (only the cluster nothing else)
    #if node == 'resonator_spectroscopy':
    #        # Performs time of flight measurement
    #        TOF_plotting=False
    #        TOF=Time_Of_Flight(Cluster("cluster", '192.0.2.72'), TOF_plotting)
    #        logger.info(f'Time of flight: {TOF}')

    print(f'{Fore.BLUE}{Style.BRIGHT}Measuring node: {node} , duration: {schedule_duration:.2f}s{Style.RESET_ALL}')

    Cluster.close_all()
    if cluster_status == ClusterStatus.dummy:
       dummy = {str(mod): ClusterType.CLUSTER_QCM_RF for mod in range(1,16)}
       dummy["16"] = ClusterType.CLUSTER_QRM_RF
       dummy["17"] = ClusterType.CLUSTER_QRM_RF
       dimension = 1
       for subspace in samplespace.values():
           dimension *= len( list(subspace.values())[0] )

       dummy_data = [ DummyBinnedAcquisitionData(data=(8,16),thres=1,avg_cnt=1) for _ in range(dimension) ]
       clusterA = Cluster("clusterA", dummy_cfg=dummy)

       # clusterB = Cluster("clusterB", dummy_cfg=dummy)
    elif cluster_status == ClusterStatus.real:
       #clusterB = Cluster("clusterB", '192.0.2.141')
       clusterA = Cluster("clusterA", lokiA_IP)



    if node == 'tof':
        result_dataset = measure_time_of_flight(clusterA)
        return result_dataset
    loki_ic = InstrumentCoordinator('loki_ic')
    loki_ic.add_component(ClusterComponent(clusterA))
    #loki_ic.add_component(ClusterComponent(clusterB))
    loki_ic.timeout(222)

    def run_measurement() -> None:
        loki_ic.prepare(compiled_schedule)
        loki_ic.start()
        loki_ic.wait_done(timeout_sec=600)

    def display_progress():
        steps = int(schedule_duration * 5)
        if cluster_status == ClusterStatus.dummy:
            progress_sleep = 0.01
        elif cluster_status == ClusterStatus.real :
            progress_sleep = 0.2
        for _ in tqdm.tqdm(range(steps), desc=node, colour='blue'):
            sleep(progress_sleep)


    thread_tqdm = threading.Thread(target=display_progress)
    thread_tqdm.start()
    thread_loki = threading.Thread(target=run_measurement)
    thread_loki.start()
    thread_loki.join()
    thread_tqdm.join()

    if cluster_status == ClusterStatus.dummy:
        clusterA.set_dummy_binned_acquisition_data(16,sequencer=0,acq_index_name='0',data=dummy_data)
        clusterA.set_dummy_binned_acquisition_data(17,sequencer=0,acq_index_name='1',data=dummy_data)
        clusterA.set_dummy_binned_acquisition_data(17,sequencer=1,acq_index_name='2',data=dummy_data)

    raw_dataset: xarray.Dataset = loki_ic.retrieve_acquisition()
    logger.info('Raw dataset acquired')

    # result_dict = raw_dataset.to_dict()
    # with open('example_ds.py','w') as f:
    #     f.write(str(result_dict))

    result_dataset = configure_dataset(raw_dataset, samplespace)
    eventid = datetime.now().strftime('%Y%m-%d-%H%M%S-') + f'{node}-'+ str(uuid4())
    result_dataset.to_netcdf(data_directory / eventid)

    result_dataset_complex = to_complex_dataset(result_dataset)

    loki_ic.stop()
    logger.info('Finished measurement')
    # print(result_dataset)

    return result_dataset_complex

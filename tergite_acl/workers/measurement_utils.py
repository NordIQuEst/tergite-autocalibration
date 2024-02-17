# from workers.dataset_utils import configure_dataset, handle_ro_freq_optimization, to_real_dataset, save_dataset
# import time
# import xarray
# from logger.tac_logger import logger
# import threading
# import tqdm
# import numpy as np
# from utilities.status import ClusterStatus
# from workers.hardware_utils import SpiDAC
# from quantify_scheduler.instrument_coordinator.instrument_coordinator import CompiledSchedule
# from colorama import init as colorama_init
# from colorama import Fore
# from colorama import Style
# colorama_init()
#
# def execute_schedule(
#         compiled_schedule: CompiledSchedule,
#         lab_ic,
# ) -> xarray.Dataset:
#
#     logger.info('Starting measurement')
#     cluster_status = ClusterStatus.real
#     schedule_duration = compiled_schedule.get_schedule_duration()
#     print(f'schedule_duration = {Fore.CYAN}{Style.BRIGHT}{schedule_duration:.2f} sec{Style.RESET_ALL}')
#
#     def run_measurement() -> None:
#         lab_ic.prepare(compiled_schedule)
#         lab_ic.start()
#         lab_ic.wait_done(timeout_sec=600)
#
#     def display_progress():
#         steps = int(schedule_duration * 5)
#         if cluster_status == ClusterStatus.dummy:
#             progress_sleep = 0.004
#         elif cluster_status == ClusterStatus.real:
#             progress_sleep = 0.2
#         for _ in tqdm.tqdm(range(steps), desc=compiled_schedule.name, colour='blue'):
#             time.sleep(progress_sleep)
#     thread_tqdm = threading.Thread(target=display_progress)
#     thread_tqdm.start()
#     thread_lab = threading.Thread(target=run_measurement)
#     thread_lab.start()
#     thread_lab.join()
#     thread_tqdm.join()
#
#     raw_dataset: xarray.Dataset = lab_ic.retrieve_acquisition()
#     lab_ic.stop()
#     logger.info('Raw dataset acquired')
#
#     return raw_dataset
#
#
# class MeasurementFactory:
#
#     def select(self, node):
#         if node.name in ['coupler_spectroscopy', 'coupler_resonator_spectroscopy']:
#             return CouplerSpectroscopyMeasurement(node)
#         else:
#             return SingleQubitsMeasurement(node)
#
#
# class SingleQubitsMeasurement:
#     def __init__(self, node):
#         self.node = node
#
#     def measure(self, node, compiled_schedule, ic, data_path):
#         raw_dataset = execute_schedule(compiled_schedule, ic)
#
#         result_dataset = configure_dataset(raw_dataset, node)
#         save_dataset(result_dataset, node, data_path)
#         if node.name == 'ro_frequency_optimization':
#             result_dataset = handle_ro_freq_optimization(result_dataset, states=[0, 1])
#         elif node.name == 'ro_frequency_optimization_gef':
#             result_dataset = handle_ro_freq_optimization(result_dataset, states=[0, 1, 2])
#         return result_dataset
#
#
# class CouplerSpectroscopyMeasurement:
#     # coupler sweeps need special treatment. For this, separate them in their own class
#
#     def __init__(self, node):
#         DAC = SpiDAC()
#         self.node = node
#         self.dac = DAC.create_spi_dac(self.node.coupler)
#         self.dc_currents = self.node.spi_samplespace['dc_currents'][self.node.coupler]
#
#     def set_current(self, current_value: float):
#         print(f'{ current_value = }')
#         print(f'{ self.dac.current() = }')
#         self.dac.current(current_value)
#         while self.dac.is_ramping():
#             print(f'ramping {self.dac.current()}')
#             time.sleep(1)
#         print('Finished ramping')
#
#
#     def measure(self, node, compiled_schedule, ic, data_path):
#         logger.info('Starting coupler spectroscopy')
#         print(f'{ self.dc_currents = }')
#         for indx, current in enumerate(self.dc_currents):
#             self.set_current(current)
#
#             raw_dataset = execute_schedule(compiled_schedule, ic)
#             dataset = configure_dataset(raw_dataset, node)
#
#             dataset = dataset.expand_dims(dim='dc_currents')
#             dataset['dc_currents'] = [current]
#
#             if indx == 0:
#                 result_dataset = dataset
#             else:
#                 result_dataset = xarray.concat([result_dataset, dataset], dim='dc_currents')
#         # TODO fix the qubit name
#         measure_qubit = node.measurement_qubit
#         coord_attrs = {'qubit':measure_qubit, 'long_name': 'dc_currents', 'units': 'NA'}
#         result_dataset.dc_currents.attrs = coord_attrs
#
#         save_dataset(result_dataset, node, data_path)
#         # TODO verify this
#         self.set_current(0)
#         # self.SPI.spi.close()
#         return result_dataset
from analysis.motzoi_analysis import MotzoiAnalysis
from analysis.resonator_spectroscopy_analysis import ResonatorSpectroscopyAnalysis, ResonatorSpectroscopy_1_Analysis
from analysis.qubit_spectroscopy_analysis import QubitSpectroscopyAnalysis
from analysis.rabi_analysis import RabiAnalysis
from analysis.ramsey_analysis import RamseyAnalysis
from analysis.T1_analysis import T1Analysis
from quantify_core.data.handling import set_datadir
# from quantify_analysis import qubit_spectroscopy_analysis, rabi_analysis, T1_analysis, XY_crosstalk_analysis, ramsey_analysis, SSRO_analysis
# from quantify_core.analysis.calibration import rotate_to_calibrated_axis
import matplotlib.patches as mpatches
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('tkagg')
import redis
set_datadir('.')

redis_connection = redis.Redis(decode_responses=True)

class BaseAnalysis():
    def __init__(self, result_dataset: xr.Dataset):
       self.result_dataset = result_dataset

       self.n_vars = len(self.result_dataset.data_vars)
       self.n_coords = len(self.result_dataset.coords)
       self.fit_numpoints = 300
       self.column_grid = 3
       self.rows = (self.n_vars + 2) // self.column_grid

       self.node_result = {}
       self.fig, self.axs = plt.subplots(
            nrows=self.rows, ncols=np.min((self.n_coords, self.column_grid)), squeeze=False
        )
       self.qoi = 0 # quantity of interest

    def update_redis_trusted_values(self,node:str, this_qubit:str,transmon_parameter:str):
        redis_connection.hset(f"transmons:{this_qubit}",f"{transmon_parameter}",self.qoi)
        redis_connection.hset(f"cs:{this_qubit}",node,'calibrated')
        self.node_result.update({this_qubit: self.qoi})


class Multiplexed_Analysis(BaseAnalysis):
    def __init__(self, result_dataset: xr.Dataset, node: str):
        if node == 'tof':
            print()
            plot()
            return

        super().__init__(result_dataset)
        for indx, var in enumerate(result_dataset.data_vars):
            this_qubit = result_dataset[var].attrs['qubit']
            ds = result_dataset[var].to_dataset()
            ds.attrs['qubit'] = this_qubit

            this_axis = self.axs[indx//self.column_grid, indx%self.column_grid]
            # this_axis.set_title(f'{node_name} for {this_qubit}')
            if node == 'resonator_spectroscopy':
                analysis_class = ResonatorSpectroscopyAnalysis
                redis_field = 'ro_freq'
            elif node == 'qubit_01_spectroscopy_pulsed':
                analysis_class = QubitSpectroscopyAnalysis
                redis_field = 'freq_01'
            elif node == 'rabi_oscillations':
                analysis_class = RabiAnalysis
                redis_field = 'mw_amp180'
            elif node == 'ramsey_correction':
                analysis_class = RamseyAnalysis
                redis_field = 'freq_01'
            elif node == 'motzoi_parameter':
                analysis_class = MotzoiAnalysis
                redis_field = 'mw_motzoi'
            elif node == 'resonator_spectroscopy_1':
                analysis_class = ResonatorSpectroscopy_1_Analysis
                redis_field = 'ro_freq_1'

            node_analysis = analysis_class(ds)
            self.qoi = node_analysis.run_fitting()

            node_analysis.plotter(this_axis)

            self.update_redis_trusted_values(node, this_qubit,redis_field)

            handles, labels = this_axis.get_legend_handles_labels()
            if node == 'qubit_01_spectroscopy_pulsed':
                hasPeak=node_analysis.has_peak()
                patch2 = mpatches.Patch(color='blue', label=f'Peak Found:{hasPeak}')
                handles.append(patch2)
            patch = mpatches.Patch(color='red', label=f'{this_qubit}')
            handles.append(patch)
            this_axis.set(title=None)
            this_axis.legend(handles=handles)

#class Multiplexed_T1_Analysis(BaseAnalysis):
#    def __init__(self, result_dataset: xr.Dataset, node: str):
#        super().__init__(result_dataset)
#        for indx, var in enumerate(result_dataset.data_vars):
#            this_qubit = result_dataset[var].attrs['qubit']
#            ds = result_dataset[var].to_dataset()
#
#            this_axis = self.axs[indx//self.column_grid, indx%self.column_grid]
#            # this_axis.set_title(f'{node_name} for {this_qubit}')
#            node_analysis = T1Analysis(ds)
#            T1_time = node_analysis.model_fit()
#            T1_micros=T1_time*1e6
#
#            self.qoi = T1_time
#
#            node_analysis.plotter(this_axis)
#
#            handles, labels = this_axis.get_legend_handles_labels()
#            patch = mpatches.Patch(color='red', label=f'{this_qubit}')
#            handles.append(patch)
#            patch2=mpatches.Patch(color='green', label=f'{T1_micros} μs')
#            handles.append(patch2)
#            this_axis.set(title=None)
#            this_axis.legend(handles=handles)
#
#            #if node_name == 'rabi_frequency' or node_name == 'rabi_oscillations_BATCHED':
#            #    self.update_redis_trusted_values(node_name, this_qubit,'mw_amp180',latex)
#            #if node_name == 'rabi_12_frequency' or node_name == 'rabi_oscillations_12_BATCHED':
#            #    self.update_redis_trusted_values(node_name, this_qubit,'mw_ef_amp180',latex)
#
#        #self.node_result.update({'measurement_dataset':result_dataset.to_dict()})
#
#class Multiplexed_Punchout_Analysis(BaseAnalysis):
#    def __init__(self, result_dataset: xr.Dataset, node: str):
#        super().__init__(result_dataset)
#        for indx, var in enumerate(result_dataset.data_vars):
#            this_qubit = result_dataset[var].attrs['qubit']
#            ds = result_dataset[var].to_dataset()
#            #breakpoint()
#
#            N_amplitudes = ds.dims[f'ro_amplitudes{this_qubit}']
#            # print(f'{ N_amplitudes = }')
#            # norm_factors = np.array([max(ds.y0[ampl].values) for ampl in range(N_amplitudes)])
#            # ds[f'y{this_qubit}'] = ds.y0 / norm_factors[:,None]
#            raw_values = np.abs(ds[f'y{this_qubit}'].values)
#            normalized_values = raw_values / raw_values.max(axis=0)
#            ds[f'y{this_qubit}'].values = normalized_values
#
#            this_axis = self.axs[indx//self.column_grid, indx%self.column_grid]
#
#            ds[f'y{this_qubit}'].plot(x=f'ro_frequencies{this_qubit}', ax=this_axis)
#            # this_axis.set_title(f'{node_name} for {this_qubit}')
#
#            handles, labels = this_axis.get_legend_handles_labels()
#            patch = mpatches.Patch(color='red', label=f'{this_qubit}')
#            handles.append(patch)
#            this_axis.set(title=None)
#            this_axis.legend(handles=handles)

from analysis.resonator_spectroscopy_analysis import ResonatorSpectroscopyAnalysis
from analysis.qubit_spectroscopy_analysis import QubitSpectroscopyAnalysis
from analysis.rabi_analysis import RabiAnalysis
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
        print(f'\n--------> {transmon_parameter} = { self.qoi }<--------\n')
        redis_connection.hset(f"transmons:{this_qubit}",f"{transmon_parameter}",self.qoi)
        redis_connection.hset(f"cs:{this_qubit}",node,'calibrated')
        self.node_result.update({this_qubit: self.qoi})

class Multiplexed_Resonator_Spectroscopy_Analysis(BaseAnalysis):
    def __init__(self, result_dataset: xr.Dataset, node: str):
        super().__init__(result_dataset)
        for indx, var in enumerate(result_dataset.data_vars):
            this_qubit = result_dataset[var].attrs['qubit']
            ds = result_dataset[var].to_dataset()
            node_analysis = ResonatorSpectroscopyAnalysis(dataset=ds)
            node_analysis.run_fitting()
            fitting_results = node_analysis.fit_results
            fitting_model = fitting_results['hanger_func_complex_SI']
            fit_result = fitting_model.values

            fitted_resonator_frequency = fit_fr = fit_result['fr']
            fit_Ql = fit_result['Ql']
            fit_Qe = fit_result['Qe']
            fit_ph = fit_result['theta']
            # print(f'{ fit_Ql = }')

            minimum_freq = fit_fr / (4*fit_Qe*fit_Ql*np.sin(fit_ph)) * (
                            4*fit_Qe*fit_Ql*np.sin(fit_ph)
                          - 2*fit_Qe*np.cos(fit_ph)
                          + fit_Ql
                          + np.sqrt(  4*fit_Qe**2
                                    - 4*fit_Qe*fit_Ql*np.cos(fit_ph)
                                    + fit_Ql**2 )
                          )

            self.qoi = minimum_freq
            # PLOT THE FIT -- ONLY FOR S21 MAGNITUDE
            this_axis = self.axs[indx//self.column_grid, indx%self.column_grid]
            fitting_model.plot_fit(this_axis,numpoints = self.fit_numpoints,xlabel=None, title=None)
            this_axis.axvline(minimum_freq,c='blue',ls='solid',label='frequency at min')
            this_axis.axvline(fitted_resonator_frequency,c='magenta',ls='dotted',label='fitted frequency')
            # this_axis.set_title(f'{node} for {this_qubit}')


            self.update_redis_trusted_values(node, this_qubit,'ro_freq')

            handles, labels = this_axis.get_legend_handles_labels()
            patch = mpatches.Patch(color='red', label=f'{this_qubit}')
            handles.append(patch)
            this_axis.set(title=None)
            this_axis.legend(handles=handles)


class Multiplexed_Two_Tones_Spectroscopy_Analysis(BaseAnalysis):
    def __init__(self, result_dataset: xr.Dataset, node: str):
        super().__init__(result_dataset)
        for indx, var in enumerate(result_dataset.data_vars):
            this_qubit = result_dataset[var].attrs['qubit']
            ds = result_dataset[var].to_dataset()

            this_axis = self.axs[indx//self.column_grid, indx%self.column_grid]
            # this_axis.set_title(f'{node_name} for {this_qubit}')
            node_analysis = QubitSpectroscopyAnalysis(ds)
            rough_qubit_frequency = node_analysis.run_fitting()

            self.qoi = rough_qubit_frequency

            node_analysis.plotter(this_axis)

            self.update_redis_trusted_values(node, this_qubit,'freq_01')

            hasPeak=node_analysis.has_peak()
            handles, labels = this_axis.get_legend_handles_labels()
            patch = mpatches.Patch(color='red', label=f'{this_qubit}')
            patch2 = mpatches.Patch(color='blue', label=f'Peak Found:{hasPeak}')
            handles.append(patch)
            handles.append(patch2)
            this_axis.set(title=None)
            this_axis.legend(handles=handles)

class Multiplexed_Rabi_Analysis(BaseAnalysis):
    def __init__(self, result_dataset: xr.Dataset, node: str):
        super().__init__(result_dataset)
        for indx, var in enumerate(result_dataset.data_vars):
            this_qubit = result_dataset[var].attrs['qubit']
            ds = result_dataset[var].to_dataset()

            this_axis = self.axs[indx//self.column_grid, indx%self.column_grid]
            # this_axis.set_title(f'{node_name} for {this_qubit}')
            node_analysis = RabiAnalysis(ds)
            pi_pulse_amplitude = node_analysis.run_fitting()

            self.qoi = pi_pulse_amplitude

            node_analysis.plotter(this_axis)

            self.update_redis_trusted_values(node, this_qubit,'mw_amp180')

            handles, labels = this_axis.get_legend_handles_labels()
            patch = mpatches.Patch(color='red', label=f'{this_qubit}')
            handles.append(patch)
            this_axis.set(title=None)
            this_axis.legend(handles=handles)


class Multiplexed_T1_Analysis(BaseAnalysis):
    def __init__(self,result_dataset,node_name):
        super().__init__(result_dataset)
        for indx, this_coord in enumerate(result_dataset.coords):
            ds = _from_coord_to_dataset(this_coord, result_dataset)

            this_qubit = ds.attrs['qubit_name']
            this_axis = self.axs[indx//self.column_grid, indx%self.column_grid]
            # this_axis.set_title(f'{node_name} for {this_qubit}')
            T1_result = T1_analysis.T1Analysis(ds)
            T1_time = T1_result.model_fit()
            T1_micros=T1_time*1e6

            self.qoi = T1_time
            print(f'{ node_name = }')
            latex = ''

            T1_result.plotter(this_axis)

            handles, labels = this_axis.get_legend_handles_labels()
            patch = mpatches.Patch(color='red', label=f'{this_qubit}')
            handles.append(patch)
            patch2=mpatches.Patch(color='green', label=f'{T1_micros} μs')
            handles.append(patch2)
            this_axis.set(title=None)
            this_axis.legend(handles=handles)

            #if node_name == 'rabi_frequency' or node_name == 'rabi_oscillations_BATCHED':
            #    self.update_redis_trusted_values(node_name, this_qubit,'mw_amp180',latex)
            #if node_name == 'rabi_12_frequency' or node_name == 'rabi_oscillations_12_BATCHED':
            #    self.update_redis_trusted_values(node_name, this_qubit,'mw_ef_amp180',latex)

        self.node_result.update({'measurement_dataset':result_dataset.to_dict()})

class Multiplexed_Punchout_Analysis(BaseAnalysis):
    def __init__(self, result_dataset: xr.Dataset, node: str):
        super().__init__(result_dataset)
        for indx, var in enumerate(result_dataset.data_vars):
            this_qubit = result_dataset[var].attrs['qubit']
            ds = result_dataset[var].to_dataset()
            #breakpoint()

            N_amplitudes = ds.dims[f'ro_amplitudes{this_qubit}']
            # print(f'{ N_amplitudes = }')
            # norm_factors = np.array([max(ds.y0[ampl].values) for ampl in range(N_amplitudes)])
            # ds[f'y{this_qubit}'] = ds.y0 / norm_factors[:,None]
            raw_values = np.abs(ds[f'y{this_qubit}'].values)
            normalized_values = raw_values / raw_values.max(axis=0)
            ds[f'y{this_qubit}'].values = normalized_values

            this_axis = self.axs[indx//self.column_grid, indx%self.column_grid]

            ds[f'y{this_qubit}'].plot(x=f'ro_frequencies{this_qubit}', ax=this_axis)
            # this_axis.set_title(f'{node_name} for {this_qubit}')

            handles, labels = this_axis.get_legend_handles_labels()
            patch = mpatches.Patch(color='red', label=f'{this_qubit}')
            handles.append(patch)
            this_axis.set(title=None)
            this_axis.legend(handles=handles)
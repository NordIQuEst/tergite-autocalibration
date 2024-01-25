import numpy as np
import xarray as xr
from utilities.redis_helper import fetch_redis_params

class NRabiAnalysis():
    def  __init__(self,dataset: xr.Dataset):
        data_var = list(dataset.data_vars.keys())[0]
        coord = list(dataset[data_var].coords.keys())[0]
        self.S21 = dataset[data_var].values
        self.independents = dataset[coord].values
        self.fit_results = {}
        self.qubit = dataset[data_var].attrs['qubit']
        dataset[f'y{self.qubit}'].values = np.abs(self.S21)
        self.dataset = dataset

    def run_fitting(self):
        mw_amplitude_key = 'mw_amplitudes_sweep' + self.qubit
        mw_amplitudes = self.dataset[mw_amplitude_key].size
        sums = []
        for this_amplitude_index in range(mw_amplitudes):
            this_sum = sum(np.abs(self.dataset[f'y{self.qubit}'][this_amplitude_index].values))
            sums.append(this_sum)

        index_of_max = np.argmax(np.array(sums))
        self.previous_amplitude = fetch_redis_params('mw_amp180',self.qubit)
        self.optimal_amp180 = self.dataset[mw_amplitude_key][index_of_max].values + self.previous_amplitude

        return [self.optimal_amp180]

    def plotter(self, axis):
        datarray = self.dataset[f'y{self.qubit}']
        qubit = self.qubit

        datarray.plot(ax=axis, x=f'mw_amplitudes_sweep{qubit}',cmap='RdBu_r')
        axis.set_xlabel('mw amplitude correction')
        axis.axvline(self.optimal_amp180-fetch_redis_params('mw_amp180',self.qubit), c='k', lw=4,linestyle ='--')

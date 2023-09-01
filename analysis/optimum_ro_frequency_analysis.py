"""
Module containing a class that fits data from a resonator spectroscopy experiment.
"""
import numpy as np
from quantify_core.analysis import fitting_models as fm
import redis
import xarray as xr

model = fm.ResonatorModel()
redis_connection = redis.Redis(decode_responses=True)

class OptimalROFrequencyAnalysis():
    """
    Analysis that fits the data of resonator spectroscopy experiments
    and extractst the optimal RO frequency.
    """
    def __init__(self, dataset: xr.Dataset):
        breakpoint()
        data_var = list(dataset.data_vars.keys())[0]
        coord = list(dataset[data_var].coords.keys())[0]

        self.S21 = dataset[data_var].values
        self.frequencies = dataset[coord].values
        self.fit_results = {}

    def run_fitting(self):

        #Fetch the resulting measurement variables from self
        S21 = self.S21
        frequencies = self.frequencies

        # Gives an initial guess for the model parameters and then fits the model to the data.
        guess = model.guess(S21, f=frequencies)
        fit_result = model.fit(S21, params=guess, f=frequencies)
        self.fitting_model = model.fit(S21, params=guess, f=frequencies)

        fit_result = self.fitting_model.values

        fitted_resonator_frequency = fit_fr = fit_result['fr']
        fit_Ql = fit_result['Ql']
        fit_Qe = fit_result['Qe']
        fit_ph = fit_result['theta']

        # analytical expression, probably an interpolation of the fit would be better
        self.minimum_freq = fit_fr / (4*fit_Qe*fit_Ql*np.sin(fit_ph)) * (
                        4*fit_Qe*fit_Ql*np.sin(fit_ph)
                      - 2*fit_Qe*np.cos(fit_ph)
                      + fit_Ql
                      + np.sqrt(  4*fit_Qe**2
                                - 4*fit_Qe*fit_Ql*np.cos(fit_ph)
                                + fit_Ql**2 )
                      )
        return self.minimum_freq

    def plotter(self,ax):
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('|S21| (V)')
        self.fitting_model.plot_fit(ax,numpoints = 400,xlabel=None, title=None)
        ax.axvline(self.minimum_freq,c='blue',ls='solid',label='frequency at min')
        ax.grid()

#class ResonatorSpectroscopy_1_Analysis(ResonatorSpectroscopyAnalysis):
#    def __init__(self, dataset: xr.Dataset):
#        self.dataset = dataset
#        super().__init__(self.dataset)
#    def plotter(self,ax):
#        #breakpoint()
#        this_qubit = self.dataset.attrs['qubit']
#        ax.set_xlabel('Frequency (Hz)')
#        ax.set_ylabel('|S21| (V)')
#        ro_freq = float(redis_connection.hget(f'transmons:{this_qubit}', 'ro_freq'))
#        self.fitting_model.plot_fit(ax,numpoints = 400,xlabel=None, title=None)
#        ax.axvline(self.minimum_freq,c='green',ls='solid',label='frequency |1> ')
#        ax.axvline(ro_freq,c='blue',ls='dashed',label='frequency |0>')
#        ax.grid()
#
#class ResonatorSpectroscopy_2_Analysis(ResonatorSpectroscopyAnalysis):
#    def __init__(self, dataset: xr.Dataset):
#        self.dataset = dataset
#        super().__init__(self.dataset)
#    def plotter(self,ax):
#        this_qubit = self.dataset.attrs['qubit']
#        ax.set_xlabel('Frequency (Hz)')
#        ax.set_ylabel('|S21| (V)')
#        ro_freq = float(redis_connection.hget(f'transmons:{this_qubit}', 'ro_freq'))
#        ro_freq_1 = float(redis_connection.hget(f'transmons:{this_qubit}', 'ro_freq_1'))
#        self.fitting_model.plot_fit(ax,numpoints = 400,xlabel=None, title=None)
#        ax.axvline(self.minimum_freq,c='red',ls='solid',label='frequency |2>')
#        ax.axvline(ro_freq_1,c='green',ls='dashed',label='frequency |1>')
#        ax.axvline(ro_freq,c='blue',ls='dashed',label='frequency |0>')
#        ax.grid()

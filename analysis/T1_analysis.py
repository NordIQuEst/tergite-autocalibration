import numpy as np
import lmfit
from quantify_core.analysis.fitting_models import ExpDecayModel
import xarray as xr

class T1Analysis():
    def  __init__(self,dataset: xr.Dataset):
        data_var = list(dataset.data_vars.keys())[0]
        coord = list(dataset[data_var].coords.keys())[0]
        self.S21 = dataset[data_var].values
        self.independents = dataset[coord].values
        self.fit_results = {}
        self.qubit = dataset[data_var].attrs['qubit']

    def run_fitting(self):
        model = ExpDecayModel()
        
        self.magnitudes = np.absolute(self.S21)
        delays = self.independents

        guess = model.guess(data=self.magnitudes, delay=delays)

        fit_result = model.fit(self.magnitudes, params=guess, t=delays)
        
        self.fit_delays = np.linspace( delays[0], delays[-1], 400)
        self.fit_y = model.eval(fit_result.params, **{model.independent_vars[0]: self.fit_delays})
        #self.dataset['fit_delays'] = self.fit_delays
        #self.dataset['fit_y'] = ('fit_delays',fit_y)
        return fit_result.params['tau'].value

    def plotter(self,ax):
    	
        ax.plot( self.fit_delays , self.fit_y,'r-',lw=3.0)
        ax.plot(self.independents, self.magnitudes,'bo-',ms=3.0)
        ax.set_title(f'T1 experiment for {self.qubit}')
        ax.set_xlabel('Delay (s)')
        ax.set_ylabel('|S21| (V)')
        
        ax.grid()
 

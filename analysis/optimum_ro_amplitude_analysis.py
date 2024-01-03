"""
Module containing a class that fits data from a resonator spectroscopy experiment.
"""
import numpy as np
import redis
import xarray as xr
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import confusion_matrix,ConfusionMatrixDisplay
import matplotlib.pyplot as plt
from numpy.linalg import inv

redis_connection = redis.Redis(decode_responses=True)

class OptimalROAmplitudeAnalysis():
    """
    Analysis that  extracts the optimal RO amplitude.
    """
    def __init__(self, dataset: xr.Dataset):
        self.dataset = dataset
        self.qubit = dataset.attrs['qubit']
        self.data_var = list(dataset.data_vars.keys())[0]

        for coord in dataset.coords:
            if 'amplitudes' in str(coord):
                self.amplitude_coord = coord
            elif 'state' in str(coord):
                self.state_coord = coord
            elif 'shot' in str(coord):
                self.shot_coord = coord
        self.independents = dataset[self.state_coord].values
        self.amplitudes = dataset.coords[self.amplitude_coord]
        self.shots = len(dataset[self.shot_coord].values)
        self.fit_results = {}

    def run_fitting(self):
        self.fidelities = []
        self.cms = []
        for indx, ro_amplitude in enumerate(self.amplitudes):
            y = np.repeat(self.independents,self.shots)
            IQ_complex = np.array([])
            for state in self.independents:
                IQ_complex_0 = self.dataset[self.data_var].isel({self.amplitude_coord:[indx],self.state_coord:state})
                IQ_complex = np.append(IQ_complex,IQ_complex_0)
            I = IQ_complex.real.flatten()
            Q = IQ_complex.imag.flatten()
            IQ = np.array([I,Q]).T
            lda = LinearDiscriminantAnalysis(solver = "svd", store_covariance=True)
            # breakpoint()
            y_pred = lda.fit(IQ,y).predict(IQ)

            # cm = confusion_matrix(y,y_pred)
            # disp = ConfusionMatrixDisplay(confusion_matrix=cm)
            # disp.plot()
            # plt.show()
            cm_norm = confusion_matrix(y,y_pred,normalize='true')
            assignment = np.trace(cm_norm)/len(self.independents)
            # print(f'{cm_norm = }')
            # print(f'{assignment = }')
            self.fidelities.append(assignment)
            self.cms.append(cm_norm)
        
        for i, f in enumerate(self.fidelities):
            if i > 1:
                if f < self.fidelities[i-1] and f < self.fidelities[i-2] and f > np.mean(self.fidelities):
                    self.optimal_index = i
        self.optimal_index = np.argmax(self.fidelities)
        self.optimal_amplitude = self.amplitudes.values[self.optimal_index]
        self.optimal_inv_cm = inv(self.cms[self.optimal_index])
        inv_cm_str = ",".join(str(element) for element in list(self.optimal_inv_cm.flatten()))
        # breakpoint()
        return [self.optimal_amplitude,inv_cm_str]

    def plotter(self,ax):
        this_qubit = self.dataset.attrs['qubit']
        ax.set_xlabel('RO amplitude')
        ax.set_ylabel('assignment fidelity')
        ax.plot(self.amplitudes, self.fidelities)
        ax.plot(self.optimal_amplitude, self.fidelities[self.optimal_index], '*')

        ax.grid()

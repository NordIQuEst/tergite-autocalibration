import numpy as np
import xarray as xr
from utilities.redis_helper import fetch_redis_params
import lmfit
from quantify_core.analysis.fitting_models import fft_freq_phase_guess
from utilities.QPU_connections_visualization import edge_group

import matplotlib.pyplot as plt

# Cosine function that is fit to Rabi oscillations
def cos_func(
    drive_amp: float,
    oscillation_frequency: float,
    amplitude: float,
    offset: float,
    phase: float = 0,
) -> float:
    return amplitude * np.cos(2 * np.pi * oscillation_frequency * drive_amp + phase) + offset

class ChevronModel(lmfit.model.Model):
    """
    Generate a cosine model that can be fit to oscillation data.
    """
    def __init__(self, *args, **kwargs):
        # Pass in the defining equation so the user doesn't have to later.
        super().__init__(cos_func, *args, **kwargs)

        # Enforce oscillation oscillation frequency is positive
        self.set_param_hint("oscillation_frequency", min=0)
        self.set_param_hint("duration", expr="1/oscillation_frequency", vary=False)

        # Fix the phase at pi so that the ouput is at a minimum when drive_amp=0
        self.set_param_hint("phase", min = -3.5, max = 3.5)

        # Pi-pulse amplitude can be derived from the oscillation frequency
        self.set_param_hint("swap", expr="1/(2*oscillation_frequency)-phase", vary=False)


    def guess(self, data, min_freq, **kws) -> lmfit.parameter.Parameters:
        drive_amp = kws.get("drive_amp", None)
        if drive_amp is None:
            return None

        amp_guess = np.abs(max(data) - min(data)) / 2  # amp is positive by convention
        offs_guess = np.mean(data)

        # Frequency guess is obtained using a fast fourier transform (FFT).
        (freq_guess, _) = fft_freq_phase_guess(data, drive_amp)

        self.set_param_hint("oscillation_frequency", value=freq_guess, min=min_freq)
        self.set_param_hint("amplitude", value=amp_guess, min=0)
        self.set_param_hint("offset", value=offs_guess)

        params = self.make_params()
        return lmfit.models.update_param_vals(params, self.prefix, **kws)

class CZChevronAnalysis():
    def  __init__(self,dataset: xr.Dataset):
        data_var = list(dataset.data_vars.keys())[0]
        self.S21 = dataset[data_var].values
        self.fit_results = {}
        self.qubit = dataset[data_var].attrs['qubit']
        dataset[f'y{self.qubit}'].values = np.abs(self.S21)
        self.dataset = dataset

    def run_fitting(self):
        # return [0,0]
        self.testing_group = 0
        self.freq = self.dataset[f'cz_pulse_frequencies{self.qubit}'].values
        if f'cz_pulse_amplitudes{self.qubit}' in self.dataset.coords:
            self.independent_coord = f'cz_pulse_amplitudes{self.qubit}'
        elif f'cz_pulse_durations{self.qubit}' in self.dataset.coords:
            self.independent_coord = f'cz_pulse_durations{self.qubit}'
        else:
            raise ValueError('Invalid Coord')
        self.amp = self.dataset[self.independent_coord].values
        magnitudes = self.dataset[f'y{self.qubit}'].values

        self.magnitudes = (magnitudes - np.min(magnitudes))/(np.max(magnitudes)-np.min(magnitudes))
        self.magnitudes = np.transpose(self.magnitudes)

        model = ChevronModel()

        # values = [[np.linalg.norm(u) for u in v] for v in self.dataset[f'y{self.qubit}_']]
        fit_results = []

        for magnitude in self.magnitudes:
            # magnitude = np.transpose(values)[15]

            fit_amplitudes = np.linspace( self.amp[0], self.amp[-1], 400)
            guess = model.guess(magnitude, drive_amp=self.amp, min_freq=1/self.amp[-1])
            fit_result = model.fit(magnitude, params=guess, drive_amp=self.amp)
            fit_y = model.eval(fit_result.params, **{model.independent_vars[0]: fit_amplitudes})

            # # discard nonsensical fits
            # if fit_result.rsquared > 0.8:
            #     fit_results.append(fit_result)
            fit_results.append(fit_result)

            # print( fit_result.params['oscillation_frequency'])
            # print( fit_result.params['duration'])
            # print( fit_result.params['amplitude'])
            # print( fit_result.rsquared)
            # plt.plot(self.amp,magnitude, '.r')
            # plt.plot(fit_amplitudes,fit_y,'--b')
            # plt.show()
        qois = np.transpose([[np.abs(fit.result.params[p].value) for p in ['amplitude','duration']] for fit in fit_results])
        qois = np.transpose([(q-np.min(q))/np.max(q) for q in qois])


        opt_id = np.argmax(np.sum(qois,axis=1))

        self.opt_freq = self.freq[opt_id]
        cz_duration = fit_results[opt_id].result.params['duration'].value
        if int(self.qubit[1:]) % 2 == 0:
            # that extra pi is because we seek a max not a min
            phase = fit_results[opt_id].result.params['phase'].value
            optimal_phase = phase - np.sign(phase) * np.pi
            qubit_type = 'target'
        else:
            optimal_phase = fit_results[opt_id].result.params['phase'].value
            qubit_type = 'control'

        # self.opt_cz = fit_results[opt_id].result.params['oscillation_frequency'].value
        self.opt_cz = cz_duration * ( 2 * np.pi - optimal_phase) / 2 / np.pi
        self.opt_swap = fit_results[opt_id].result.params['swap'].value

        return [self.opt_freq,self.opt_cz]

    def plotter(self,axis):
        datarray = self.dataset[f'y{self.qubit}']
        qubit = self.qubit
        datarray.plot(ax=axis, x=self.independent_coord,cmap='RdBu_r')
        # # fig = axis.pcolormesh(amp,freq,magnitudes,shading='nearest',cmap='RdBu_r')
        axis.scatter(
            self.opt_cz,self.opt_freq,
            c='r',
            label = 'CZ Duration = {:.1f} ns'.format(self.opt_cz*1e9),
            marker='X',s=150,
            edgecolors='k', linewidth=1.0,zorder=10
        )
        # plt.scatter(opt_swap,opt_freq,c='b',label = 'SWAP12 Duration= {:.2f} V'.format(opt_swap),marker='X',s=200,edgecolors='k', linewidth=1.5,zorder=10)
        axis.hlines(
            self.opt_freq,self.amp[0],
            self.amp[-1],
            label = 'Frequency Detuning = {:.2f} MHz'.format(self.opt_freq/1e6),
            colors='k',
            linestyles='--',
            linewidth=1.5
        )
        axis.vlines(self.opt_cz,self.freq[0],self.freq[-1],colors='k',linestyles='--',linewidth=1.5)
        axis.legend(loc = 'lower center', bbox_to_anchor=(-0.15, -0.36, 1.4, .102), mode='expand', ncol=2,
                    title = 'Optimal Gate Parameters', columnspacing=200,borderpad=1)
        # # cbar = plt.colorbar(fig)
        # # cbar.set_label('|2>-state Population', labelpad=10)
        # axis.set_ylim([self.freq[0],self.freq[-1]])
        # axis.set_ylim([self.amp[0],self.amp[-1]])
        axis.set_xlabel('Parametric Drive Durations (s)')
        axis.set_ylabel('Frequency Detuning (Hz)')

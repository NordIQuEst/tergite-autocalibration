import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import importlib
import tergite_acl.lib.analysis.randomized_benchmarking_analysis as rnb
import tergite_acl.lib.analysis.optimum_ro_amplitude_analysis as roa
importlib.reload(rnb)


ds = xr.open_dataset('data_dir/20240220/20240220-171349-867-88367b-ro_amplitude_optimization_gef/dataset.hdf5')
# print(f'{ ds.yq21.attrs = }')
ds = ds.isel(ReIm=0) + 1j * ds.isel(ReIm=1)
#---
ro = roa.OptimalROAmplitudeAnalysis
#---
qubit = 'q14'
yq = ds[f'y{qubit}'].isel({f'ro_amplitudes{qubit}': [0]})

I = yq.real.values.flatten()
Q = yq.imag.values.flatten()

shots = 10

I0 = yq.real[:shots]
Q0 = yq.imag[:shots]
I1 = yq.real[shots:2*shots]
Q1 = yq.imag[shots:2*shots]
I2 = yq.real[2*shots:]
Q2 = yq.imag[2*shots:]

# y = ds.qubit_statesq13.values
y = np.tile(np.array([0,1], dtype=np.int16), shots)
# y = np.repeat(np.array([0,1,2], dtype=np.int16), 1000)
# y = np.random.randint(2, size=3000)
print(f'{ sum(y) = }')

IQ = np.array([I, Q]).T
lda = LinearDiscriminantAnalysis(solver = "svd", store_covariance=True)

# run the discrimination, y_classified are the classified levels
y_classified = lda.fit(IQ,y).predict(IQ)

tp = y == y_classified # True Positive
cm_norm = confusion_matrix(y,y_classified,normalize='true')
assign = np.trace(cm_norm) / 3
print(f'{ assign = }')
disp = ConfusionMatrixDisplay(confusion_matrix=cm_norm)
# disp.plot()

tp0 = tp[y == 0] # true positive levels when sending 0
tp1 = tp[y == 1] # true positive levels when sending 1
tp2 = tp[y == 2] # true positive levels when sending 2

IQ0 = IQ[y == 0] # IQ when sending 0
IQ1 = IQ[y == 1] # IQ when sending 1
IQ2 = IQ[y == 2] # IQ when sending 2

IQ0_tp = IQ0[ tp0] # True Positive when sending 0
IQ0_fp = IQ0[~tp0]
IQ1_tp = IQ1[ tp1] # True Positive when sending 1
IQ1_fp = IQ1[~tp1]
IQ2_tp = IQ2[ tp2] # True Positive when sending 2
IQ2_fp = IQ2[~tp2]

IQ0_positives = [IQ0_tp,IQ0_fp]
IQ1_positives = [IQ1_tp,IQ1_fp]
IQ2_positives = [IQ2_tp,IQ2_fp]

print(f'{ len(IQ0_tp) = }')
print(f'{ len(IQ1_tp) = }')
print(f'{ len(IQ2_tp) = }')

# I2 = yq12.real[2*shots:]
# Q2 = yq12.imag[2*shots:]
mark_size = 40
plt.scatter(IQ0_tp[:, 0], IQ0_tp[:, 1], marker=".", s=mark_size, color="red", label='send 0 and read 0')
plt.scatter(IQ0_fp[:, 0], IQ0_fp[:, 1], marker="x", s=mark_size, color="orange",)
plt.scatter(IQ1_tp[:, 0], IQ1_tp[:, 1], marker=".", s=mark_size, color="blue", label='send 1 and read 1')
plt.scatter(IQ1_fp[:, 0], IQ1_fp[:, 1], marker="x", s=mark_size, color="dodgerblue",)
plt.scatter(IQ2_tp[:, 0], IQ2_tp[:, 1], marker=".", s=mark_size, color="green")
plt.scatter(IQ2_fp[:, 0], IQ2_fp[:, 1], marker="x", s=mark_size, color="lime",)

# plt.plot( I0, Q0,'bo')
# plt.plot( I1, Q1,'ro')
# plt.plot( I2, Q2,'ko')
plt.show()

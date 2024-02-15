# qubits = [ 'q16','q17','q18','q19','q20','q21','q22','q23','q24','q25']
# qubits = [ 'q18','q19','q20','q21','q22','q23','q24','q25']
qubits = ['q12','q13','q14']
# couplers = ['q12_q13','q13_q14' ]
couplers = ['q13_q14']

'''
node reference
  punchout
  resonator_spectroscopy
  qubit_01_spectroscopy_multidim
  qubit_01_spectroscopy_pulsed
  rabi_oscillations
  ramsey_fringes
  resonator_spectroscopy_1
  qubit_12_spectroscopy_pulsed
  qubit_12_spectroscopy_multidim
  rabi_oscillations_12
  ramsey_correction_12
  resonator_spectroscopy_2
  ro_frequency_optimization
  ro_frequency_optimization_gef
  ro_amplitude_optimization_gef
  coupler_spectroscopy
  coupler_resonator_spectroscopy
  motzoi_parameter
  n_rabi_oscillations
  randomized_benchmarking
  state_discrimination
  T1
  T2
  T2_echo
  randomized_benchmarking
  check_cliffords
  cz_chevron
  cz_optimize_chevron
  reset_chevron
  cz_calibration
  cz_calibration_ssro
  cz_dynamic_phase
'''

user_requested_calibration = {
    'target_node': 'ro_amplitude_optimization_gef',
    'all_qubits': qubits,
    'couplers': couplers,
}

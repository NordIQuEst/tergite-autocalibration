# qubits = [ 'q16','q17','q18','q19','q20','q21','q22','q23','q24','q25']
# qubits = [ 'q17','q18','q19','q20','q21','q22','q23','q24','q25']
qubits = ['q21','q22']
#qubits = ['q16', 'q17', 'q19', 'q21', 'q22', 'q23', 'q25']
# qubits = ['q16', 'q17']
#qubits = [ 'q21','q22']
couplers = ['q21_q22']

'''
node reference
  punchout
  resonator_spectroscopy
  qubit_01_spectroscopy_multidim
  qubit_01_spectroscopy_pulsed
  qubit_12_spectroscopy_multidim
  rabi_oscillations
  ramsey_fringes
  resonator_spectroscopy_1
  qubit_12_spectroscopy_pulsed
  rabi_oscillations_12
  resonator_spectroscopy_2
  coupler_spectroscopy
  coupler_resonator_spectroscopy
  motzoi_parameter
  n_rabi_oscillations
  T1
  cz_chevron
  cz_calibration
'''

user_requested_calibration = {
    'target_node': 'resonator_spectroscopy',
    'all_qubits': qubits,
    'couplers': couplers,
    # 'node_dictionary' : {'coupled_qubits': ['q21','q22']},
}

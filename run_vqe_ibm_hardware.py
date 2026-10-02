import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib.pyplot as plt

from qiskit_nature.units import DistanceUnit
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_algorithms import NumPyMinimumEigensolver

from qiskit.circuit.library import EfficientSU2
from qiskit.primitives import StatevectorEstimator
from scipy.optimize import minimize

from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, EstimatorV2 as RuntimeEstimator

# -----------------------------------------------------------------------------
# 1. MOLECULAR CHEMISTRY SETUP & EXACT FCI GROUND TRUTH
# -----------------------------------------------------------------------------
print("[1/5] Evaluating molecular Hamiltonian via PySCF (H2 @ 0.74 A, STO-3G)...")
driver = PySCFDriver(
    atom="H 0 0 0; H 0 0 0.74",
    basis="sto-3g",
    charge=0,
    spin=0,
    unit=DistanceUnit.ANGSTROM,
)
problem = driver.run()
mapper = JordanWignerMapper()
qubit_op = mapper.map(problem.hamiltonian.second_q_op())

exact_solver = NumPyMinimumEigensolver()
exact_result = exact_solver.compute_minimum_eigenvalue(qubit_op)
v_nn = problem.nuclear_repulsion_energy
exact_total_energy = exact_result.eigenvalue.real + v_nn
print(f"      Exact FCI Analytical Baseline: {exact_total_energy:.6f} Ha")

# -----------------------------------------------------------------------------
# 2. LOCAL PRE-OPTIMIZATION (COBYLA on Ideal Simulator)
# -----------------------------------------------------------------------------
print("[2/5] Pre-optimizing HEA trial parameters locally on CPU...")
ansatz = EfficientSU2(
    num_qubits=4,
    su2_gates=["ry", "rz"],
    entanglement="linear",
    reps=1,
)

ideal_estimator = StatevectorEstimator()
def cost_func(params):
    job = ideal_estimator.run([(ansatz, qubit_op, params)])
    return float(job.result()[0].data.evs)

np.random.seed(42)
initial_theta = np.zeros(ansatz.num_parameters)
opt_result = minimize(cost_func, initial_theta, method="COBYLA", options={"maxiter": 80})
optimal_circuit = ansatz.assign_parameters(opt_result.x)

# -----------------------------------------------------------------------------
# 3. CONNECT TO IBM QUANTUM & TRANSPILE FOLDED CIRCUITS
# -----------------------------------------------------------------------------
print("[3/5] Connecting to IBM Quantum Platform...")
service = QiskitRuntimeService(channel="ibm_quantum_platform")
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=4)
print(f"      Assigned Hardware Backend: {backend.name}")

# Transpile once to lock physical layout and basis gates
probe_transpiled = transpile(optimal_circuit, backend=backend, optimization_level=1)

# FIX: Extract strictly the 4 physical integer indices mapped to your circuit
virtual_bits = probe_transpiled.layout.initial_layout.get_virtual_bits()
best_layout_list = [virtual_bits[q] for q in optimal_circuit.qubits]

mapped_qubit_op = qubit_op.apply_layout(probe_transpiled.layout)
print(f"      Base Transpiled Depth on {backend.name}: {probe_transpiled.depth()}")

def fold_circuit(circuit, scale_factor):
    """Digital unitary circuit folding: U -> U (U^dagger U)^n"""
    if scale_factor == 1:
        return circuit.copy()
    n_folds = (scale_factor - 1) // 2
    inv = circuit.inverse()
    folded = circuit.copy()
    for _ in range(n_folds):
        folded.compose(inv, inplace=True)
        folded.compose(circuit, inplace=True)
    return folded

lambda_scales = np.array([1, 3, 5])
transpiled_circuits = []

for l in lambda_scales:
    f_circ = fold_circuit(optimal_circuit, l)
    # Pass the clean list of 4 integers to avoid the ancilla crash
    t_circ = transpile(f_circ, backend=backend, initial_layout=best_layout_list, optimization_level=0)
    transpiled_circuits.append(t_circ)
    print(f"      λ = {l} -> Native Hardware Depth: {t_circ.depth()}")

# -----------------------------------------------------------------------------
# 4. SUBMIT SINGLE BATCHED EXPERIMENT VIA ESTIMATOR V2
# -----------------------------------------------------------------------------
print("\n[4/5] Submitting batched experiment to physical QPU...")
pubs = [(circ, mapped_qubit_op) for circ in transpiled_circuits]

estimator = RuntimeEstimator(mode=backend)
if hasattr(estimator.options, "default_shots"):
    estimator.options.default_shots = 4096

job = estimator.run(pubs)
print("=" * 68)
print(f"      ACTIVE JOB ID: {job.job_id()}")
print("=" * 68)
print("Job successfully submitted. Waiting in cloud queue...")
print("You can track status at https://quantum.cloud.ibm.com/workloads")

# Blocking wait for physical hardware results
result = job.result()

hardware_measured_energies = []
for i, l in enumerate(lambda_scales):
    ev = float(result[i].data.evs)
    tot_energy = ev + v_nn
    hardware_measured_energies.append(tot_energy)
    print(f"      QPU Measured E (λ = {l}): {tot_energy:.6f} Ha")

hardware_measured_energies = np.array(hardware_measured_energies)

# -----------------------------------------------------------------------------
# 5. LINEAR ZNE EXTRAPOLATION
# -----------------------------------------------------------------------------
print("\n[5/5] Extrapolating to zero-noise limit (λ -> 0)...")
poly_fit = np.polyfit(lambda_scales, hardware_measured_energies, deg=1)
slope, zne_mitigated_energy = poly_fit[0], poly_fit[1]

raw_error = abs(hardware_measured_energies[0] - exact_total_energy)
mitigated_error = abs(zne_mitigated_energy - exact_total_energy)

print("\n" + "=" * 68)
print(f"       REAL HARDWARE RESULTS ({backend.name})")
print("=" * 68)
print(f"Exact Analytical FCI Baseline:        {exact_total_energy:.6f} Ha")
print(f"Raw QPU Measured Energy (λ = 1):      {hardware_measured_energies[0]:.6f} Ha (Error: {raw_error * 1000:.2f} mHa)")
print(f"ZNE Mitigated Energy (λ = 0):         {zne_mitigated_energy:.6f} Ha (Error: {mitigated_error * 1000:.2f} mHa)")
print(f"Chemical Accuracy Benchmark:          < 1.60 mHa (0.001594 Ha)")
print(f"Mitigation Status:                    {'Achieved (< 1.6 mHa)' if mitigated_error < 0.0016 else 'Partially Mitigated'}")
print("=" * 68)

# -----------------------------------------------------------------------------
# 6. EXPORT REAL HARDWARE FIGURE
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 5.2), dpi=300)
x_fit = np.linspace(0, 5.5, 100)
ax.plot(x_fit, slope * x_fit + zne_mitigated_energy, color="#1f77b4", linestyle="--", linewidth=1.8, label=f"Linear ZNE Fit ($a\\lambda + b$)")
ax.scatter(lambda_scales, hardware_measured_energies, color="#d62728", s=90, zorder=5, label=f"IBM QPU ({backend.name})")
ax.scatter([0], [zne_mitigated_energy], color="#2ca02c", marker="*", s=180, zorder=6, label=f"ZNE Mitigated: {zne_mitigated_energy:.5f} Ha")
ax.axhline(exact_total_energy, color="black", linestyle="-", linewidth=1.5, alpha=0.8, label=f"Exact FCI: {exact_total_energy:.5f} Ha")
ax.fill_between(x_fit, exact_total_energy - 0.0016, exact_total_energy + 0.0016, color="gray", alpha=0.22, label="Chemical Accuracy Band (±1.6 mHa)")

ax.set_title(f"Zero-Noise Extrapolation on IBM Superconducting Hardware ({backend.name})", fontsize=12, fontweight="bold", pad=12)
ax.set_xlabel(r"Noise Scale Factor ($\lambda$)", fontsize=11)
ax.set_ylabel("Ground State Energy (Hartrees)", fontsize=11)
ax.set_xlim(-0.3, 5.5)
ax.grid(True, linestyle=":", alpha=0.6)
ax.legend(frameon=True, facecolor="white", framealpha=0.92, fontsize=9, loc="upper left")

plt.tight_layout()
plt.savefig("vqe_zne_hardware_real.png")
plt.close(fig)
print("Saved real hardware figure as 'vqe_zne_hardware_real.png'.")
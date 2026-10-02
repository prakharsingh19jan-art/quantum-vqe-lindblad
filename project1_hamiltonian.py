import warnings
warnings.filterwarnings("ignore")

from qiskit_nature.units import DistanceUnit
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_algorithms import NumPyMinimumEigensolver

# 1. Molecular geometry: H2 at 0.74 Angstroms in STO-3G basis
driver = PySCFDriver(
    atom="H 0 0 0; H 0 0 0.74",
    basis="sto-3g",
    charge=0,
    spin=0,
    unit=DistanceUnit.ANGSTROM,
)
problem = driver.run()

# 2. Extract fermionic Hamiltonian & apply Jordan-Wigner mapping
fermionic_op = problem.hamiltonian.second_q_op()
mapper = JordanWignerMapper()
qubit_op = mapper.map(fermionic_op)

# 3. Exact analytical reference (FCI) via matrix diagonalization
exact_solver = NumPyMinimumEigensolver()
exact_result = exact_solver.compute_minimum_eigenvalue(qubit_op)

electronic_energy = exact_result.eigenvalue.real
nuclear_repulsion = problem.nuclear_repulsion_energy
total_ground_state_energy = electronic_energy + nuclear_repulsion

# 4. Formatted Metrics
print("=" * 65)
print(f"Active Qubits Required:            {qubit_op.num_qubits}")
print(f"Total Unique Pauli Strings:        {len(qubit_op)}")
print(f"Nuclear Repulsion Energy (V_NN):   {nuclear_repulsion:.6f} Ha")
print(f"Exact Electronic Energy (E_e):     {electronic_energy:.6f} Ha")
print(f"Exact Analytical Ground Energy:    {total_ground_state_energy:.6f} Ha")
print("=" * 65)

print("\nSample Generated Pauli Strings (Coefficients in Hartrees):")
for pauli, coeff in list(qubit_op.to_list())[:6]:
    print(f"  {pauli} : {coeff.real:+.6f}")
print("=" * 65)
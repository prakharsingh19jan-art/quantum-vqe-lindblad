import warnings
warnings.filterwarnings("ignore")

from qiskit_nature.units import DistanceUnit
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
from qiskit.circuit.library import EfficientSU2
from qiskit import transpile
from qiskit.providers.fake_provider import GenericBackendV2

# 1. Chemistry Setup: H2 at equilibrium bond length (0.74 Angstroms, STO-3G)
driver = PySCFDriver(
    atom="H 0 0 0; H 0 0 0.74",
    basis="sto-3g",
    charge=0,
    spin=0,
    unit=DistanceUnit.ANGSTROM,
)
problem = driver.run()
mapper = JordanWignerMapper()

# 2. Chemistry Ansatz: UCCSD
initial_state = HartreeFock(
    problem.num_spatial_orbitals,
    problem.num_particles,
    mapper,
)
uccsd_circuit = UCCSD(
    problem.num_spatial_orbitals,
    problem.num_particles,
    mapper,
    initial_state=initial_state,
)

# 3. Hardware-Efficient Ansatz (HEA): EfficientSU2
hea_circuit = EfficientSU2(
    num_qubits=4,
    su2_gates=["ry", "rz"],
    entanglement="linear",
    reps=1,
    insert_barriers=True,
)

# 4. Transpile against a representative 5-qubit superconducting backend
backend = GenericBackendV2(num_qubits=5)
transpiled_uccsd = transpile(uccsd_circuit, backend=backend, optimization_level=1)
transpiled_hea = transpile(hea_circuit, backend=backend, optimization_level=1)

# 5. Extract Hardware Metrics
ops_uccsd = transpiled_uccsd.count_ops()
ops_hea = transpiled_hea.count_ops()

# GenericBackendV2 natively decomposes 2-qubit interactions into 'cz' or 'cx'
two_qubit_uccsd = ops_uccsd.get("cz", 0) + ops_uccsd.get("cx", 0) + transpiled_uccsd.num_nonlocal_gates()
two_qubit_hea = ops_hea.get("cz", 0) + ops_hea.get("cx", 0) + transpiled_hea.num_nonlocal_gates()

# Correct for duplicate counting if num_nonlocal_gates is identical to direct count
two_qubit_uccsd = transpiled_uccsd.num_nonlocal_gates()
two_qubit_hea = transpiled_hea.num_nonlocal_gates()

# 6. Formatted Benchmark Table
print("=" * 68)
print("          ANSATZ HARDWARE BENCHMARK METRICS (4 QUBITS)")
print("=" * 68)
print(f"{'Metric':<26} | {'UCCSD (Chemistry)':<18} | {'HEA (Hardware-Opt)':<18}")
print("-" * 68)
print(f"{'Parameter Count':<26} | {uccsd_circuit.num_parameters:<18} | {hea_circuit.num_parameters:<18}")
print(f"{'Total Transpiled Gates':<26} | {sum(ops_uccsd.values()):<18} | {sum(ops_hea.values()):<18}")
print(f"{'2-Qubit Entangling Gates':<26} | {two_qubit_uccsd:<18} | {two_qubit_hea:<18}")
print(f"{'Circuit Depth':<26} | {transpiled_uccsd.depth():<18} | {transpiled_hea.depth():<18}")
print("=" * 68)
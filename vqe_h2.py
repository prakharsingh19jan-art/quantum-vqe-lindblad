import warnings
warnings.filterwarnings("ignore")
from qiskit_nature.units import DistanceUnit
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
from qiskit.primitives import StatevectorEstimator as Estimator
from qiskit_algorithms import VQE
from qiskit_algorithms.optimizers import SLSQP

# Step 1: Define the H2 molecule
driver = PySCFDriver(
    atom="H 0 0 0; H 0 0 0.735",
    basis="sto3g",
    charge=0,
    spin=0,
    unit=DistanceUnit.ANGSTROM,
)
problem = driver.run()

# Step 2: Map the molecular problem to qubits
mapper = JordanWignerMapper()
qubit_op = mapper.map(problem.second_q_ops()[0])

# Step 3: Build the ansatz (the "guessing engine")
ansatz = UCCSD(
    problem.num_spatial_orbitals,
    problem.num_particles,
    mapper,
    initial_state=HartreeFock(
        problem.num_spatial_orbitals,
        problem.num_particles,
        mapper,
    ),
)

# Step 4: Set up VQE with a classical optimizer
optimizer = SLSQP(maxiter=100)
estimator = Estimator()
vqe = VQE(estimator, ansatz, optimizer)

# Step 5: Run VQE and get the ground state energy
result = vqe.compute_minimum_eigenvalue(qubit_op)
print("VQE computed ground state energy:", result.eigenvalue.real)

# Step 6: Compare against the exact classical answer
from qiskit_algorithms import NumPyMinimumEigensolver
exact_solver = NumPyMinimumEigensolver()
exact_result = exact_solver.compute_minimum_eigenvalue(qubit_op)
print("Exact ground state energy:", exact_result.eigenvalue.real)
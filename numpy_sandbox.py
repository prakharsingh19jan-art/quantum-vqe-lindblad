import numpy as np

print("=== 1. DEFINING A QUBIT IN STATE |0> ===")
# A qubit state is a vector with two complex numbers: [amplitude of 0, amplitude of 1]
qubit = np.array([1.0, 0.0], dtype=complex)
print(f"Starting state |0>: {qubit}")
print(f"Shape: {qubit.shape} (a 1D vector of length 2)\n")

print("=== 2. CREATING THE NOT (PAULI-X) GATE ===")
# A quantum gate is a 2x2 matrix: [[row 1], [row 2]]
X_gate = np.array([
    [0.0, 1.0],
    [1.0, 0.0]
], dtype=complex)
print("X Gate Matrix:")
print(X_gate)
print(f"Shape: {X_gate.shape} (2 rows by 2 columns)\n")

print("=== 3. APPLYING THE GATE (X @ qubit) ===")
# The '@' symbol performs row-by-column matrix multiplication
flipped_qubit = X_gate @ qubit
print(f"Resulting state |1>: {flipped_qubit}\n")

print("=== 4. TIME DISCRETIZATION FOR DECAY SIMULATIONS ===")
# Cut continuous time from 0 to 5 microseconds into 6 discrete snapshots
time_points = np.linspace(0, 5, 6)
print(f"Time checkpoints (microseconds): {time_points}")
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib.pyplot as plt
import qutip as qt

# -----------------------------------------------------------------------------
# 1. EMPIRICAL HARDWARE CALIBRATION METRICS (IBM Superconducting Transmon)
# -----------------------------------------------------------------------------
T1 = 120.0   # Relaxation time in microseconds[cite: 3]
T2 = 80.0    # Dephasing time in microseconds[cite: 3]

# Calculate decay rates and pure dephasing: 1/T2 = 1/(2*T1) + 1/T_phi[cite: 3]
gamma_1 = 1.0 / T1
gamma_2 = 1.0 / T2
gamma_phi = gamma_2 - (0.5 * gamma_1)

if gamma_phi < 0:
    raise ValueError("Physical violation: 1/T2 must be >= 1/(2*T1)")

T_phi = 1.0 / gamma_phi

print("=" * 65)
print("     PROJECT 2: OPEN QUANTUM SYSTEM (LINDBLAD DYNAMICS)")
print("=" * 65)
print(f"Energy Relaxation Time (T1):       {T1:.2f} us")
print(f"Transverse Dephasing Time (T2):     {T2:.2f} us")
print(f"Pure Dephasing Time (T_phi):       {T_phi:.2f} us")
print("=" * 65)

# -----------------------------------------------------------------------------
# 2. OPERATORS & HAMILTONIAN
# -----------------------------------------------------------------------------
sigma_z = qt.sigmaz()
sigma_m = qt.destroy(2)  # |0><1| Lowering operator
H = 0.0 * sigma_z        # Rotating frame resonance

# -----------------------------------------------------------------------------
# 3. EXPLICIT COLLAPSE (JUMP) OPERATORS
# -----------------------------------------------------------------------------
L1 = np.sqrt(gamma_1) * sigma_m
L2 = np.sqrt(gamma_phi / 2.0) * sigma_z
c_ops = [L1, L2]

# -----------------------------------------------------------------------------
# 4. INITIAL STATE: EQUAL SUPERPOSITION |+>
# -----------------------------------------------------------------------------
psi0 = (qt.basis(2, 0) + qt.basis(2, 1)).unit()
rho0 = qt.ket2dm(psi0)

# -----------------------------------------------------------------------------
# 5. LINDBLAD TIME EVOLUTION (mesolve) - QuTiP 5 Syntax
# -----------------------------------------------------------------------------
tlist = np.linspace(0, 300, 600)
result = qt.mesolve(H, rho0, tlist, c_ops=c_ops)

# Extract diagonal populations and off-diagonal coherences using dm.full()
rho_11 = [np.real(dm.full()[1, 1]) for dm in result.states]
rho_01 = [np.abs(dm.full()[0, 1]) for dm in result.states]

# -----------------------------------------------------------------------------
# 6. PUBLICATION-GRADE VISUALIZATION EXPORT
# -----------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True, dpi=300)

# Top Panel: T1 Relaxation
ax1.plot(tlist, rho_11, color="#d95f02", linewidth=2.0, label=r"Simulated Population $\rho_{11}(t)$")
ax1.plot(tlist, 0.5 * np.exp(-tlist / T1), color="black", linestyle="--", linewidth=1.2, label=r"Analytical $0.5 e^{-t/T_1}$ Envelope")
ax1.set_title(r"Open System Dynamics: Lindblad Master Equation ($T_1 / T_2$ Decay)", fontsize=13, fontweight="bold", pad=10)
ax1.set_ylabel(r"Population $\rho_{11}$", fontsize=11)
ax1.grid(True, linestyle=":", alpha=0.6)
ax1.legend(loc="upper right", frameon=True, facecolor="white")

# Bottom Panel: T2 Dephasing
ax2.plot(tlist, rho_01, color="#1b9e77", linewidth=2.0, label=r"Simulated Coherence $|\rho_{01}(t)|$")
ax2.plot(tlist, 0.5 * np.exp(-tlist / T2), color="black", linestyle="--", linewidth=1.2, label=r"Analytical $0.5 e^{-t/T_2}$ Envelope")
ax2.set_xlabel(r"Evolution Time ($\mu$s)", fontsize=11)
ax2.set_ylabel(r"Coherence $|\rho_{01}|$", fontsize=11)
ax2.grid(True, linestyle=":", alpha=0.6)
ax2.legend(loc="upper right", frameon=True, facecolor="white")

plt.tight_layout()
plt.savefig("lindblad_decoherence_dynamics.png")
print("Saved 2-panel decoherence plot as 'lindblad_decoherence_dynamics.png'.")
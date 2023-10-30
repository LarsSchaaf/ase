from ase.stress import get_elasticity_tensor
import numpy as np

from ase.calculators.emt import EMT
from ase.build import bulk
from ase.filters import ExpCellFilter
from ase.optimize import BFGS

atoms = bulk('Au')
atoms.calc = EMT()

C_ijkl = get_elasticity_tensor(atoms)
for i in range(3):
    for j in range(3):
        print(f'C_ijkl[{i}, {j}] =')
        for k in range(3):
            for l in range(3):
                print(round(C_ijkl[i,j,k,l], 2), end=' ')
            print()
        print()
    print()

def CellBFGS(atoms, alpha=70, bulk_modulus=148, poisson_ratio=0.3):
    """
        Create advanced BFGS optimizer for bulk systems, with 

        Parameters:
           bulk_modulus  Bulk Modulus of the isotropic system used to set up
                         the Hessian (in GPa). Default value 500 GPa corresponds
                         approximately to diamond.

           poisson_ratio Poisson ratio of the isotropic system ysed to set up
                         the initial Hessian (unitless, between -1 and 0.5).
                         Default value is 0.3.

           alpha         Diagonal elements of initial BFGS Hessian for atomic
                         coordinates (in eV/Å^2). Default value of 70
                         approximately. alpha is also used to suppress
                         collective rotation of all unit cell vectors (the
                         energy is invariant to all orthonormal
                         transformations of the unit cell). 

    """
    assert np.all(atoms.pbc)
 
    bulk_modulus = 0.00624150907 * bulk_modulus # GPa to eV / Å^3
    atoms_and_cell = ExpCellFilter(atoms)
    relax = BFGS(atoms_and_cell, alpha=alpha)
    g = np.eye(3)

    # https://scienceworld.wolfram.com/physics/LameConstants.html
    _lambda = 3 * bulk_modulus * (poisson_ratio) / (1 + 1 * poisson_ratio)
    _mu = _lambda * (1 - 2 * poisson_ratio) / (2 * poisson_ratio)

    # https://en.wikipedia.org/wiki/Elasticity_tensor
    g_ij = np.eye(3)

    # Construct 4th rank Elasticity tensor for isotropic systems
    C_ijkl = _lambda * np.einsum('ij,kl->ijkl',g_ij,g_ij)
    C_ijkl += _mu * (np.einsum('ik,jl->ijkl', g_ij, g_ij) +
                     np.einsum('il,kj->ijkl', g_ij, g_ij))

    # Supplement the tensor with suppression of pure rotations (which are right now 0 eigenvalues)
    # Loop over all basis vectors of skew symmetric real matrix
    #for i,j in ((0,1),(0,2),(1,2)):
    #    Q = np.zeros((3,3))
    #    Q[i,j], Q[j,i] = 1, -1
    #    C_ijkl += np.einsum('ij,kl->ijkl', Q, Q) * alpha / 2

    # Update the Hessian initial guess
    relax.H0[-9:, -9:] = C_ijkl.reshape((9,9)) #* atoms.cell.volume

    return relax
np.set_printoptions(precision=3)
relax = CellBFGS(atoms)
print(np.round(relax.H0[-9:, -9:],3))
print(np.round(C_ijkl.reshape((9,9)),3))


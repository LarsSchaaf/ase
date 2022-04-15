import pytest

from ase.build import molecule
from ase.calculators.dftb import Dftb

@pytest.mark.calculator_lite
@pytest.mark.calculator('dftb')
def test_xtb_static(dftb_factory):
    atoms = molecule('H2O')
    calc = Dftb(atoms=atoms, Hamiltonian_='xTB', Hamiltonian_Method='GFN2-xTB')
    atoms.calc = calc

    e = atoms.get_potential_energy()
    assert e == pytest.approx(-137.97459675495645)

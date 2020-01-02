import os
import subprocess
from unittest import SkipTest
from ase.test import require
from ase.test.dftb import Si_Si_skf
from ase.calculators.dftb import Dftb
from ase.build import bulk

require('dftb')

with open('./Si-Si.skf', 'w') as f:
    f.write(Si_Si_skf)

os.environ['DFTB_PREFIX'] = './'

# We need to get the DFTB+ version to know
# whether to skip this test or not.
# For this, we need to run DFTB+ and grep
# the version from the output header.
cmd = os.environ['ASE_DFTB_COMMAND'].split()[0]
proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

lines = ''
for line in proc.stdout:
    l = line.decode()
    if 'DFTB+' in l and ('version' in l.lower() or 'release' in l.lower()):
        version = l[l.index('DFTB+'):]
        break
    lines += l + '\n'
else:
    raise RuntimeError('Could not parse DFTB+ version ' + lines)

if '17.1' not in version:
    msg = 'Band structure properties not present in results.tag for ' + version
    raise SkipTest(msg)

# The actual testing starts here
calc = Dftb(label='dftb',
            kpts=(3,3,3),
            Hamiltonian_SCC='Yes',
            Hamiltonian_SCCTolerance=1e-5,
            Hamiltonian_MaxAngularMomentum_Si='d')

atoms = bulk('Si')
atoms.set_calculator(calc)
atoms.get_potential_energy()

efermi = calc.get_fermi_level()
assert abs(efermi - -2.90086680996455) < 1.

# DOS does not currently work because of 
# missing "get_k_point_weights" function
#from ase.dft.dos import DOS
#dos = DOS(calc, width=0.2)
#d = dos.get_dos()
#e = dos.get_energies()
#print(d, e)

calc = Dftb(atoms=atoms,
            label='dftb',
            kpts={'path':'WGXWLG', 'npoints':50},
            Hamiltonian_SCC='Yes',
            Hamiltonian_MaxSCCIterations=1,
            Hamiltonian_ReadInitialCharges='Yes',
            Hamiltonian_MaxAngularMomentum_Si='d')

atoms.set_calculator(calc)
calc.calculate(atoms)

calc.results['fermi_levels'] = [efermi]
bs = calc.band_structure()

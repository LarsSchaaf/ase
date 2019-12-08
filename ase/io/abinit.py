import re
from ase.units import Hartree, Bohr
import numpy as np
"""
This module contains functionality for reading an ASE
Atoms object in ABINIT input format.

"""

def read_abinit_in(fd):
    """Import ABINIT input file.

    Reads cell, atom positions, etc. from abinit input file
    """

    from ase import Atoms, units

    lines = []
    for line in fd.readlines():
        meat = line.split('#', 1)[0]
        lines.append(meat)
    tokens = ' '.join(lines).lower().split()

    # note that the file can not be scanned sequentially

    index = tokens.index("acell")
    unit = 1.0
    if(tokens[index + 4].lower()[:3] != 'ang'):
        unit = units.Bohr
    acell = [unit * float(tokens[index + 1]),
             unit * float(tokens[index + 2]),
             unit * float(tokens[index + 3])]

    index = tokens.index("natom")
    natom = int(tokens[index+1])

    index = tokens.index("ntypat")
    ntypat = int(tokens[index+1])

    index = tokens.index("typat")
    typat = []
    for i in range(natom):
        t = tokens[index+1+i]
        if '*' in t:  # e.g. typat 4*1 3*2 ...
            typat.extend([int(t) for t in ((t.split('*')[1] + ' ') * int(t.split('*')[0])).split()])
        else:
            typat.append(int(t))
        if len(typat) == natom: break

    index = tokens.index("znucl")
    znucl = []
    for i in range(ntypat):
        znucl.append(int(tokens[index+1+i]))

    index = tokens.index("rprim")
    rprim = []
    for i in range(3):
        rprim.append([acell[i]*float(tokens[index+3*i+1]),
                      acell[i]*float(tokens[index+3*i+2]),
                      acell[i]*float(tokens[index+3*i+3])])

    # create a list with the atomic numbers
    numbers = []
    for i in range(natom):
        ii = typat[i] - 1
        numbers.append(znucl[ii])

    # now the positions of the atoms
    if "xred" in tokens:
        index = tokens.index("xred")
        xred = []
        for i in range(natom):
            xred.append([float(tokens[index+3*i+1]),
                         float(tokens[index+3*i+2]),
                         float(tokens[index+3*i+3])])
        atoms = Atoms(cell=rprim, scaled_positions=xred, numbers=numbers,
                      pbc=True)
    else:
        if "xcart" in tokens:
            index = tokens.index("xcart")
            unit = units.Bohr
        elif "xangst" in tokens:
            unit = 1.0
            index = tokens.index("xangst")
        else:
            raise IOError(
                "No xred, xcart, or xangs keyword in abinit input file")

        xangs = []
        for i in range(natom):
            xangs.append([unit*float(tokens[index+3*i+1]),
                          unit*float(tokens[index+3*i+2]),
                          unit*float(tokens[index+3*i+3])])
        atoms = Atoms(cell=rprim, positions=xangs, numbers=numbers, pbc=True)

    try:
        ii = tokens.index('nsppol')
    except ValueError:
        nsppol = None
    else:
        nsppol = int(tokens[ii + 1])

    if nsppol == 2:
        index = tokens.index('spinat')
        magmoms = [float(tokens[index + 3 * i + 3]) for i in range(natom)]
        atoms.set_initial_magnetic_moments(magmoms)

    return atoms


keys_with_units = {
    'toldfe': 'eV',
    'tsmear': 'eV',
    'paoenergyshift': 'eV',
    'zmunitslength': 'Bohr',
    'zmunitsangle': 'rad',
    'zmforcetollength': 'eV/Ang',
    'zmforcetolangle': 'eV/rad',
    'zmmaxdispllength': 'Ang',
    'zmmaxdisplangle': 'rad',
    'ecut': 'eV',
    'pawecutdg': 'eV',
    'dmenergytolerance': 'eV',
    'electronictemperature': 'eV',
    'oneta': 'eV',
    'onetaalpha': 'eV',
    'onetabeta': 'eV',
    'onrclwf': 'Ang',
    'onchemicalpotentialrc': 'Ang',
    'onchemicalpotentialtemperature': 'eV',
    'mdmaxcgdispl': 'Ang',
    'mdmaxforcetol': 'eV/Ang',
    'mdmaxstresstol': 'eV/Ang**3',
    'mdlengthtimestep': 'fs',
    'mdinitialtemperature': 'eV',
    'mdtargettemperature': 'eV',
    'mdtargetpressure': 'eV/Ang**3',
    'mdnosemass': 'eV*fs**2',
    'mdparrinellorahmanmass': 'eV*fs**2',
    'mdtaurelax': 'fs',
    'mdbulkmodulus': 'eV/Ang**3',
    'mdfcdispl': 'Ang',
    'warningminimumatomicdistance': 'Ang',
    'rcspatial': 'Ang',
    'kgridcutoff': 'Ang',
    'latticeconstant': 'Ang'}


def write_abinit_in(fd, atoms, param=None, species=None):
    from ase.calculators.calculator import kpts2mp
    if param is None:
        param = {}

    if species is None:
        species = list(set(atoms.numbers))

    inp = {}
    inp.update(param)
    for key in ['xc', 'smearing', 'kpts', 'pps', 'raw']:
        del inp[key]

    smearing = param.get('smearing')
    if 'tsmear' in param or 'occopt' in param:
        assert smearing is None

    if smearing is not None:
        inp['occopt'] = {'fermi-dirac': 3,
                         'gaussian': 7}[smearing[0].lower()]
        inp['tsmear'] = smearing[1]

    inp['natom'] = len(atoms)

    if 'nbands' in param:
        inp['nband'] = param.nbands
        del inp['nbands']

    # ixc is set from paw/xml file. Ignore 'xc' setting then.
    if param.get('pps') not in ['pawxml']:
        if 'ixc' not in param:
            inp['ixc'] = {'LDA': 7,
                          'PBE': 11,
                          'revPBE': 14,
                          'RPBE': 15,
                          'WC': 23}[param.xc]

    magmoms = atoms.get_initial_magnetic_moments()
    if magmoms.any():
        inp['nsppol'] = 2
        fd.write('spinat\n')
        for n, M in enumerate(magmoms):
            fd.write('%.14f %.14f %.14f\n' % (0, 0, M))
    else:
        inp['nsppol'] = 1

    for key in sorted(inp):
        value = inp[key]
        unit = keys_with_units.get(key)
        if unit is None:
            fd.write('%s %s\n' % (key, value))
        else:
            if 'fs**2' in unit:
                value /= fs**2
            elif 'fs' in unit:
                value /= fs
            fd.write('%s %e %s\n' % (key, value, unit))

    if param.raw is not None:
        for line in param.raw:
            if isinstance(line, tuple):
                fd.write(' '.join(['%s' % x for x in line]) + '\n')
            else:
                fd.write('%s\n' % line)

    fd.write('#Definition of the unit cell\n')
    fd.write('acell\n')
    fd.write('%.14f %.14f %.14f Angstrom\n' % (1.0, 1.0, 1.0))
    fd.write('rprim\n')
    if atoms.number_of_lattice_vectors != 3:
        raise RuntimeError('Abinit requires a 3D cell, but cell is {}'
                           .format(atoms.cell))
    for v in atoms.cell:
        fd.write('%.14f %.14f %.14f\n' %  tuple(v))

    fd.write('chkprim 0 # Allow non-primitive cells\n')

    fd.write('#Definition of the atom types\n')
    fd.write('ntypat %d\n' % (len(species)))
    fd.write('znucl {}\n'.format(' '.join(str(Z) for Z in species)))
    fd.write('#Enumerate different atomic species\n')
    fd.write('typat')
    fd.write('\n')
    types = []
    for Z in atoms.numbers:
        for n, Zs in enumerate(species):
            if Z == Zs:
                types.append(n + 1)
    n_entries_int = 20  # integer entries per line
    for n, type in enumerate(types):
        fd.write(' %d' % (type))
        if n > 1 and ((n % n_entries_int) == 1):
            fd.write('\n')
    fd.write('\n')

    fd.write('#Definition of the atoms\n')
    fd.write('xangst\n')
    for pos in atoms.positions:
        fd.write('%.14f %.14f %.14f\n' %  tuple(pos))

    if 'kptopt' not in param:
        # XXX This processing should probably happen higher up
        mp = kpts2mp(atoms, param.kpts)
        fd.write('kptopt 1\n')
        fd.write('ngkpt %d %d %d\n' % tuple(mp))
        fd.write('nshiftk 1\n')
        fd.write('shiftk\n')
        fd.write('%.1f %.1f %.1f\n' % tuple((np.array(mp) + 1) % 2 * 0.5))

    fd.write('chkexit 1 # abinit.exit file in the running directory terminates after the current SCF\n')




def read_stress(fd):
    # sigma(1 1)=  4.02063464E-04  sigma(3 2)=  0.00000000E+00
    # sigma(2 2)=  4.02063464E-04  sigma(3 1)=  0.00000000E+00
    # sigma(3 3)=  4.02063464E-04  sigma(2 1)=  0.00000000E+00
    pat = re.compile(r'\s*sigma\(\d \d\)=\s*(\S+)\s*sigma\(\d \d\)=\s*(\S+)')
    stress = np.empty(6)
    for i in range(3):
        line = next(fd)
        m = pat.match(line)
        assert m is not None
        s1, s2 = m.group(1, 2)
        stress[i] = float(m.group(1))
        stress[i + 3] = float(m.group(2))
    unit = Hartree / Bohr**3
    return stress / unit


def read_abinit_out(fd):
    results = {}

    def skipto(string):
        for line in fd:
            if string in line:
                return line
        raise ReadError('Not found: {}'.format(string))


    line = skipto('Version')
    m = re.match(r'\.*?Version\s+(\S+)\s+of ABINIT', line)
    assert m is not None
    results['version'] = m.group(1)

    shape_vars = {}

    skipto('echo values of preprocessed input variables')

    for line in fd:
        if '===============' in line:
            break

        tokens = line.split()
        if not tokens:
            continue

        for key in ['natom', 'nkpt', 'nband', 'ntypat']:
            if tokens[0] == key:
                shape_vars[key] = int(tokens[1])

        def consume_multiline(fd, header, headerline, nvalues, dtype):
            """Parse abinit-formatted "header + values" sections.

            Example:

                typat 1 1 1 1 1
                      1 1 1 1
            """
            tokens = headerline.split()
            assert tokens[0] == header, tokens[0]

            values = tokens[1:]
            while len(values) < nvalues:
                line = next(fd)
                values.extend(line.split())
            assert len(values) == nvalues
            values = np.array(values).astype(dtype)
            return values

        if line.lstrip().startswith('typat'):  # Avoid matching ntypat
            types = consume_multiline(fd, 'typat', line, shape_vars['natom'],
                                      int)

        if 'znucl' in line:
            znucl = consume_multiline(fd, 'znucl', line, shape_vars['ntypat'],
                                      float)

        if 'rprim' in line:
            cell = consume_multiline(fd, 'rprim', line, 9, float)
            cell = cell.reshape(3, 3)

    natoms = shape_vars['natom']
    nkpts = shape_vars['nkpt']
    nbands = shape_vars['nband']

    # Skip ahead to results:
    for line in fd:
        if 'was not enough scf cycles to converge' in line:
            raise ReadError(line)
        if 'iterations are completed or convergence reached' in line:
            break
    else:
        raise ReadError('Cannot find results section')

    def read_array(fd, nlines):
        arr = []
        for i in range(nlines):
            line = next(fd)
            arr.append(line.split()[1:])
        arr = np.array(arr).astype(float)
        return arr

    for line in fd:
        if 'cartesian coordinates (angstrom) at end' in line:
            positions = read_array(fd, natoms)
        if 'cartesian forces (eV/Angstrom) at end' in line:
            results['forces'] = read_array(fd, natoms)
        if 'Cartesian components of stress tensor (hartree/bohr^3)' in line:
            results['stress'] = read_stress(fd)

        if 'Components of total free energy (in Hartree)' in line:
            for line in fd:
                if 'Etotal' in line:
                    energy = float(line.rsplit('=', 2)[1]) * Hartree
                    results['energy'] = results['free_energy'] = energy
                    break
                    # Which of the listed energies do we take ??
        if 'END DATASET(S)' in line:
            break

    znucl_int = znucl.astype(int)
    znucl_int[znucl_int != znucl] = 0  # (Fractional Z)
    numbers = znucl_int[types - 1]

    from ase import Atoms
    atoms = Atoms(numbers=numbers,
                  positions=positions,
                  cell=cell,
                  pbc=True)

    if 0:
        print('DONE PARSING')
        print('------------')
        for key in results:
            print(key)
            val = results[key]
            if isinstance(val, np.ndarray):
                print(val.shape, val.dtype)
            else:
                print(results[key])
            print()
        print(atoms)
    results['atoms'] = atoms
    return results


def old_read_abinit_out(fd):
    text = fd.read().lower()
    results = {}

    for line in iter(text.split('\n')):
        if line.rfind('error') > -1 or line.rfind('was not enough scf cycles to converge') > -1:
            raise ReadError(line)
        if line.rfind('natom  ') > -1:
            natoms = int(line.split()[-1])

    lines = iter(text.split('\n'))
    # Stress:
    # Printed in the output in the following format [Hartree/Bohr^3]:
    # sigma(1 1)=  4.02063464E-04  sigma(3 2)=  0.00000000E+00
    # sigma(2 2)=  4.02063464E-04  sigma(3 1)=  0.00000000E+00
    # sigma(3 3)=  4.02063464E-04  sigma(2 1)=  0.00000000E+00
    for line in lines:
        if line.rfind(
            'cartesian components of stress tensor (hartree/bohr^3)') > -1:
            stress = np.empty(6)
            for i in range(3):
                entries = next(lines).split()
                stress[i] = float(entries[2])
                stress[i + 3] = float(entries[5])
            results['stress'] = stress * Hartree / Bohr**3
            break
    else:
        raise RuntimeError

    # Energy [Hartree]:
    # Warning: Etotal could mean both electronic energy and free energy!
    etotal = None
    efree = None
    if 'PAW method is used'.lower() in text:  # read DC energy according to M. Torrent
        for line in iter(text.split('\n')):
            if line.rfind('>>>>> internal e=') > -1:
                etotal = float(line.split('=')[-1])*Hartree  # second occurrence!
        for line in iter(text.split('\n')):
            if line.rfind('>>>> etotal (dc)=') > -1:
                efree = float(line.split('=')[-1])*Hartree
    else:
        for line in iter(text.split('\n')):
            if line.rfind('>>>>> internal e=') > -1:
                etotal = float(line.split('=')[-1])*Hartree  # first occurrence!
                break
        for line in iter(text.split('\n')):
            if line.rfind('>>>>>>>>> etotal=') > -1:
                efree = float(line.split('=')[-1])*Hartree
    if efree is None:
        raise RuntimeError('Total energy not found')
    if etotal is None:
        etotal = efree

    # Energy extrapolated to zero Kelvin:
    results['energy'] = (etotal + efree) / 2
    results['free_energy'] = efree

    # Forces:
    for line in lines:
        if line.rfind('cartesian forces (ev/angstrom) at end:') > -1:
            forces = []
            for i in range(natoms):
                forces.append(np.array(
                        [float(f) for f in next(lines).split()[1:]]))
            results['forces'] = np.array(forces)
            break
    else:
        raise RuntimeError

    results['nbands'] = read_number_of_bands(lines)
    results['niter'] = read_number_of_iterations(lines)
    results['magmom'] = read_magnetic_moment(lines)
    return results

def read_number_of_iterations(lines):
    niter = None
    for line in lines:
        if ' At SCF step' in line:
            niter = int(line.split()[3].rstrip(','))
    return niter

def read_number_of_bands(lines):
    nband = None
    for line in lines:
        if '     nband' in line: # nband, or nband1, nband*
            nband = int(line.split()[-1].strip())
    return nband

def read_magnetic_moment(lines):
    magmom = 0.0
    # only for spinpolarized system Magnetisation is printed
    for line in lines:
        if 'Magnetisation' in line:
            magmom = float(line.split('=')[-1].strip())
    return magmom


def read_eig(fd):
    line = next(fd)
    results = {}
    m = re.match(r'\s*Fermi \(or HOMO\) energy \(hartree\)\s*=\s*(\S+)',
                 line)
    assert m is not None
    results['fermilevel'] = float(m.group(1)) * Hartree
    # XXX TODO spin
    kpoint_weights = []
    kpoint_coords = []

    eig_skn = []
    for ispin in range(2):
        # (We don't know if we have two spins until we see next line)
        line = next(fd)
        m = re.match(r'\s*Magnetization \(Bohr magneton\)=\s*(\S+)',
                     line)
        if m is not None:
            magmom = float(m.group(1))
            results['magmom'] = magmom
            line = next(fd)

        m = re.match(r'\s*Eigenvalues \(hartree\) for nkpt\s*='
                     r'\s*(\S+)\s*k\s*points', line)
        nspins = 2 if 'SPIN' in line else 1
        assert m is not None, line
        nkpts = int(m.group(1))

        headerpattern = (r'\s*kpt#\s*\S+\s*'
                         r'nband=\s*(\d+),\s*'
                         r'wtk=([^,]+),\s*'
                         r'kpt=\s*(\S)+\s*(\S+)\s*(\S+)')


        eig_kn = []
        for ikpt in range(nkpts):
            header = next(fd)
            m = re.match(headerpattern, header)
            assert m is not None, header
            nbands = int(m.group(1))
            weight = float(m.group(2))
            kvector = np.array(m.group(3, 4, 5)).astype(float)
            if ispin == 0:
                kpoint_coords.append(kvector)
                kpoint_weights.append(float(weight))

            eig_n = []
            while len(eig_n) < nbands:
                line = next(fd)
                tokens = line.split()
                values = np.array(tokens).astype(float) * Hartree
                eig_n.extend(values)
            assert len(eig_n) == nbands
            eig_kn.append(eig_n)
            assert nbands == len(eig_kn[0])
        eig_skn.append(eig_kn)

        if nspins == 1:
            break

    eig_skn = np.array(eig_skn)
    assert eig_skn.shape == (nspins, nkpts, nbands), (eig_skn.shape, (nspins, nkpts, nbands))
    results['ibz_kpoints'] = np.array(kpoint_coords)
    results['kpoint_weights'] = np.array(kpoint_weights)
    results['eigenvalues'] = eig_skn
    return results


def read_abinit_log(fd):
    results = {}
    width = None
    nelect = None
    lines = fd.readlines()
    for line in lines:
        if 'tsmear' in line:
            results['width'] = float(line.split()[1].strip()) * Hartree
        if 'with nelect' in line:
            results['nelect'] = float(line.split('=')[1].strip())
    return results

# Copyright 2018-2021 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This module contains functions and classes to create a BasisFunction object from standard basis sets
such as STO-3G.
"""

from basis_data import STO3G


class BasisFunction:
    r"""Create a basis function object.

    A basis set is composed of a set of basis functions that are typically constructed as a linear
    combination of primitive Gaussian orbitals. For instance, a basis function in the STO-3G basis
    set is formed as

    .. math::

        \psi = c_1 G_1 + c_2 G_2 + c_3 G_3,

    where :math:`c_i` is a constant and :math:`G_i` is a Gaussian function defined as

    .. math::

        G_i = x^l y^m z^n e^{-\alpha r^2}.

    Each Gaussian function is characterized by the angular momentum numbers :math:`(l, m, n)`, which
    determine the type of the orbital, the exponents :math:`\alpha = (\alpha_x, \alpha_y, \alpha_z)`
    and the position vector :math:`r = (x, y, z)`. These parameters and the contraction coefficients
    :math:`c_i` define each specific atomic basis functions of a reference basis set such as STO-3G.

    The basis function object created by the BasisFunction class stores all the basis set parameters
    including the angular momentum, exponents, positions and coefficients of the Gaussian functions.

    The basis function object can be easily passed to the functions that compute various types of
    integrals over such functions, e.g., overlap integrals, which are essential for Hartree-Fock
    calculations.

    Args:
        l (tuple[int]): angular momentum numbers of the basis function.
        alpha (array(float)): exponents of the Gaussian functions forming the basis function
        coeff (array(float)): coefficients of the contracted Gaussian functions
        rgaus (array(float)): positions of the Gaussian functions forming the basis function
    """

    def __init__(self, l, alpha, coeff, rgaus): # pylint: disable=too-few-public-methods
        self.l = l
        self.alpha = alpha
        self.coeff = coeff
        self.rgaus = rgaus
        self.params = [self.alpha, self.coeff, self.rgaus]


def atom_basis_data(name, atom):
    r"""Generate default basis set parameters for an atom.

    This function extracts the default angular momentum and the exponents and contraction
    coefficients of Gaussian functions forming a Gaussian Type Orbital (GTO) for a given atom. These
    values are taken from the basis set data provided in ``basis_data.py``.

    Args:
        name (str): name of the basis set
        atom (str): atomic symbol of the chemical element

    Returns:
        list(tuple): tuple containing the angular momentum, the exponents and contraction
        coefficients of a basis function

    **Example**

    >>>  params = atom_basis_data('sto-3g', 'H')
    >>> print(params)
    [((0, 0, 0), [3.425250914, 0.6239137298, 0.168855404], [0.1543289673, 0.5353281423, 0.4446345422])]
    """
    basis_sets = {"sto-3g": STO3G}

    s = [(0, 0, 0)]
    p = [(0, 0, 1), (0, 1, 0), (1, 0, 0)]

    basis = basis_sets[name][atom]
    params = []
    for i, j in enumerate(basis["orbitals"]):
        if j == "S":
            params.append((s[0], basis["exponents"][i], basis["coefficients"][i]))
        elif j == "SP":
            for term in j:
                if term == "S":
                    params.append((s[0], basis["exponents"][i], basis["coefficients"][i]))
                if term == "P":
                    for l in p:
                        params.append((l, basis["exponents"][i], basis["coefficients"][i + 1]))
    return params


def mol_basis_data(name, symbols):
    r"""Generates default basis set parameters for a molecule.

    This function generates the default basis set parameters for a list of atomic symbols and
    computes the total number of basis functions for each atom.

    Args:
        name (str): name of the basis set
        symbols (list[str]): symbols of the atomic species in the molecule

    Returns:
        tuple(list, tuple): the number of basis functions and the basis set parameters for each atom
        in the molecule

    **Example**

    >>>  n_basis, params = mol_basis_data('sto-3g', ['H', 'H'])
    >>> print(n_basis)
    [1, 1]
    >>> print(params)
    (((0, 0, 0), [3.425250914, 0.6239137298, 0.168855404], [0.1543289673, 0.5353281423, 0.4446345422]),
     ((0, 0, 0), [3.425250914, 0.6239137298, 0.168855404], [0.1543289673, 0.5353281423, 0.4446345422]))
    """
    n_basis = []
    basis_set = []
    for s in symbols:
        basis = atom_basis_data(name, s)
        n_basis += [len(basis)]
        basis_set += basis
    return n_basis, tuple(basis_set)

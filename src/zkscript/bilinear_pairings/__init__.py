"""bilinear_pairings package.

This package provides subpackages for constructing Bitcoin scripts that perform bilinear pairings over multiple curves.

Subpackages:
    - bls12_381: Contains modules for constructing Bitcoin scripts that perform bilinear pairings over BLS12-381.
    - mnt4_753: Contains modules for constructing Bitcoin scripts that perform bilinear pairings over MNT4-753.
    - model: Contains modules for constructing Bitcoin scripts that perform bilinear pairings and miller loop
    computations.

Usage example:
    >>> from src.zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381
    >>>
    >>> # Script that, taken two points P, Q and some additional data, compute the pairing e(P,Q)
    >>> bls12_381_pairing = bls12_381.pairing(
    >>>     modulo_threshold = 1,  # The max size a number is allowed to reach during script execution
    >>>     check_constant = True,
    >>>     clean_constant = True,
    >>> )
    >>>
    >>> # Script that, taken two points P1, P2, P3, Q1, Q2, Q3, and some additional data, compute the product of the
    >>> # three pairings e(P1,Q1) * e(P2,Q2) * e(P3,Q3)
    >>> bls12_381_triple_pairing = bls12_381.triple_pairing(
    >>>     modulo_threshold = 1,
    >>>     check_constant = True,
    >>>     clean_constant = True,
    >>> )
"""

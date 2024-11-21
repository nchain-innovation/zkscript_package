"""groth16 package.

This package provides modules for constructing Bitcoin scripts that verify Groth16 proof over the BLS12-381 and
MNT4-753 curves.

Subpackages:
    - bls12_381: Contains a module for exporting the Groth16 Bitcoin script verifier over BLS12-381.
    - mnt4_753: Contains a module for exporting the Groth16 Bitcoin script verifier over MNT4-753.
    - model: Contains a module for constructing Bitcoin scripts that perform Groth16 proof verification.

Usage example:
    Construct a script that verifies a Groth16 zk proof over the BLS12-381 curve:

    >>> from src.zkscript.groth16.bls12_381.bls12_381 import bls12_381
    >>>
    >>> bls12_381_groth16_verifier = bls12_381.groth16_verifier(
    ...     modulo_threshold = 1,
    ...     alpha_beta = [0] * 12,                      # Dummy pairing e(alpha,beta)
    ...     minus_gamma = [0,0,0,0],                # Dummy element -gamma in G2
    ...     minus_delta = [0,0,0,0],                # Dummy element -delta in G2
    ...     gamma_abc = [[0,0],[0,0],[0,0],[0,0]],      # Dummy elements gamma_abc in G1
    ...     check_constant = True,
    ...     clean_constant = True,
    ... )
"""

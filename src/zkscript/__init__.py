"""zkscript: A Python package for generating Bitcoin SV scripts for cryptographic applications.

The `zkscript` package provides utilities and functions to generate Bitcoin SV scripts programmatically.
It supports the creation of scripts that can perform various cryptographic operations such as finite
field arithmetic, elliptic curve arithmetic, and bilinear pairings. By leveraging these scripts, it becomes possible
to construct advanced cryptographic applications such as zero-knowledge proof verification.

Usage example:
    Construct a script that verifies a Groth16 zk proof:

    >>> from src.zkscript.groth16.model.groth16 import Groth16
    >>> from src.zkscript.bilinear_pairings.bls12_381.bls12_381 import bls12_381 as bls12_381_pairing_model
    >>> from src.zkscript.bilinear_pairings.bls12_381.parameters import a, r
    >>>
    >>> bls12_381 = Groth16(
    >>>     pairing_model=bls12_381_pairing_model,
    >>>     curve_a=a,
    >>>     r=r
    >>> )
    >>>
    >>> bls12_381_groth16_verifier = bls12_381.groth16_verifier(
    >>>     modulo_threshold = 1,
    >>>     alpha_beta = [0] * 12,                      # Dummy pairing e(alpha,beta)
    >>>     minus_gamma = [0,0,0,0],                # Dummy element -gamma in G2
    >>>     minus_delta = [0,0,0,0],                # Dummy element -delta in G2
    >>>     gamma_abc = [[0,0],[0,0],[0,0],[0,0]],      # Dummy elements gamma_abc in G1
    >>>     check_constant = True,
    >>>     clean_constant = True,
    >>> )

License:
    This package is released under the license found in `LICENSE.txt <LICENSE.txt>`_ located in the project root. If you
    would like to use this package for commercial purposes, please contact research.enquiries@nchain.com.
"""

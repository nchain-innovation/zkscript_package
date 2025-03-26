"""elliptic_curves package.

This package provides modules for constructing Bitcoin scripts that perform elliptic curve operations.

Modules:
    - ec_operations_fq: Contains the EllipticCurveFq class for elliptic curve arithmetic over F_q.
    - ec_operations_fq2: Contains the EllipticCurveFq2 class for elliptic curve arithmetic over F_q^2.
    - ec_operations_fq_unrolled: Contains the EllipticCurveFqUnrolled class for elliptic curve arithmetic over F_q
    with unrolled multiplication.

Usage example:
    >>> from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
    >>>
    >>> secp256k1_MODULUS = 115792089237316195423570985008687907853269984665640564039457584007908834671663
    >>> secp256k1_script = EllipticCurveFq(q=secp256k1_MODULUS,curve_a=0,curve_b=7)
    >>>
    >>> lock = secp256k1_script.point_algebraic_addition(take_modulo=True,check_constant=True,clean_constant=True)
"""

"""fields package.

This package provides modules for constructing Bitcoin scripts that perform arithmetic operations in various finite
fields.

Modules:
    - fq2: Contains the Fq2 class for arithmetic operations over the finite field F_q^2 built as a quadratic extension
    of F_q.
    - fq4: Contains the Fq4 class for arithmetic operations over the finite field F_q^4 built as a quadratic extension
    of F_q^2.
    - fq2_over_2_residue_equal_u: Contains the Fq2Over2ResidueEqualU class inherited from Fq4 for arithmetic operations
    over the finite field F_q^4 built as a quadratic extension of F_q^2 = F_q[u] / (u^2 - NON_RESIDUE), with residue u.
    - fq6_3_over_2: Contains the Fq6 class for arithmetic operations over the finite field F_q^6 built as cubic
    extension of F_q^2.
    - fq12_2_over_3_over_2: Contains the Fq12 class for arithmetic operations over the finite field F_q^12 built as a
    quadratic extension of F_q^6, which is built as a cubic extension of F_q^2.
    - fq12_3_over_2_over_2: Contains the Fq12Cubic class for arithmetic operations over the finite field F_q^12 built as
    cubic extension of F_q^4, which is built as a quadratic extension of F_q^2.

Usage example:
    >>> from src.zkscript.fields.fq2 import Fq2
    >>> fq2_script = Fq2(q=19, non_residue=-1)
    >>> lock = fq2_script.add(
    >>>     take_modulo = True,
    >>>     check_constant = True,
    >>>     clean_constant = True,
    >>>     is_constant_reused = False
    >>> )
"""

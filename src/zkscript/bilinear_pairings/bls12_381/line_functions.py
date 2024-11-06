"""line_functions module.

This module enables constructing Bitcoin scripts that perform line evaluation for BLS12-381.
"""

from tx_engine import Script

from src.zkscript.bilinear_pairings.bls12_381.fields import fq2_script
from src.zkscript.util.utility_scripts import mod, pick, verify_bottom_constant


class LineFunctions:
    """Line evaluation for BLS12-381."""

    def __init__(self, fq2):
        """Initialise line evaluation for BLS12-381.

        Args:
            fq2: The script implementation of the field F_q^2.
        """
        self.MODULUS = fq2.MODULUS
        self.FQ2 = fq2

    def line_evaluation(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Evaluate line through T and Q at P.

        Stack input:
            - stack:    [q, ..., lambda, Q, P], `P` is in `E(F_q)`, `Q` is in `E'(F_q^2)`, the sextic twist, `lambda` is
                in F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., ev_(l_(T,Q)(P))], `ev_(l_(T,Q))(P)` is an element in F_q^12, the cubic extension of
                F_q^4
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, at the end of the execution, q is left as the ???
                element at the top of the stack.

        Preconditions:
            - `lambda` is the gradient through `T` and `Q`.
            - If `T = Q`, then the `lambda` is the gradient of the tangent at `T`.

        Returns:
            Script to evaluate a line through `T` and `Q` at `P`.

        Notes:
            - `lambda` is NOT checked in this function, it is assumed to be the gradient.
            - `ev_(l_(T,Q)(P))` does NOT include the zero in the second component, this is to optimise the script size.
        """
        # Fq2 implementation
        fq2 = self.FQ2

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Compute third component
        # After this, the stack is: lambda xQ yQ yP, altstack = [-lambda*xP]
        third_component = Script.parse_string("OP_SWAP OP_NEGATE")  # Roll xP and negate
        third_component += pick(position=7, n_elements=2)  # Pick lambda
        third_component += Script.parse_string("OP_ROT")  # Roll -xP
        third_component += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Compute second component
        # After this, the stack is: lambda xQ yQ, altstack = [third_component, yP]
        second_component = Script.parse_string("OP_TOALTSTACK")

        # Compute first component
        # After this, the stack is: -yQ + lambda*xQ, altsack = [third_component, yP]
        first_component = Script.parse_string("OP_2ROT OP_2ROT")  # Roll lambda and xQ
        first_component += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)
        first_component += Script.parse_string("OP_2SWAP")  # Roll yQ
        if take_modulo:
            first_component += fq2.subtract(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=True
            )
        else:
            first_component += fq2.subtract(take_modulo=False, check_constant=False, clean_constant=False)

        out += third_component + second_component + first_component

        if take_modulo:
            # Batched modulo operations: pull from altstack, rotate, mod out, repeat
            out += mod()
            out += mod()
            out += mod(is_constant_reused=is_constant_reused)
        else:
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 3))

        return out


line_functions = LineFunctions(fq2=fq2_script)

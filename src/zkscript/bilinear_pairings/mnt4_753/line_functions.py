"""Bitcoin scripts that perform line evaluation for MNT4-753."""

from tx_engine import Script

from src.zkscript.bilinear_pairings.mnt4_753.fields import fq2_script
from src.zkscript.util.utility_scripts import mod, verify_bottom_constant


class LineFunctions:
    """Line evaluation for MNT4-753."""

    def __init__(self, fq2):
        """Initialise line evaluation for MNT4-753.

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
            - stack:    [q, ..., lambda, Q, P], `P` is in `E(F_q)`, `Q` is in `E'(F_q^2)`, the quadratic twist,
                `lambda` is in F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., ev_(l_(T,Q)(P))], `ev_(l_(T,Q))(P)` is an element in F_q^4
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

        # Line evaluation for MNT4 returns: (lambda, Q, P) --> (-yQ + lambda * (xQ - xP*u), yP) as a point in Fq4

        # Second component
        # After this, the stack is: lambda Q xP, altstack = [yP]
        second_component = Script.parse_string("OP_TOALTSTACK")

        # First component
        # After this, the stack is: lambda yQ (xQ - xP*u)
        first_component = Script.parse_string("OP_TOALTSTACK")
        first_component += Script.parse_string("OP_2SWAP OP_FROMALTSTACK OP_SUB")
        # After this, the stack is yQ lambda * (xQ - xP*u)
        first_component += Script.parse_string("OP_2ROT")
        first_component += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        # After this, the stack is: (-yQ + lambda * (xQ - xP*u))_0, altstack = [yP, (-yQ + lambda * (xQ - xP*u))_1]
        first_component += Script.parse_string("OP_ROT OP_SUB OP_TOALTSTACK")
        first_component += Script.parse_string("OP_SWAP OP_SUB")

        out += second_component + first_component

        if take_modulo:
            batched_modulo = Script()

            if clean_constant is None and is_constant_reused is None:
                raise ValueError(
                    f"If take_modulo is set, both clean_constant: {clean_constant} \
                        and is_constant_reused: {is_constant_reused} must be set."
                )

            if clean_constant:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            batched_modulo += mod(stack_preparation="")
            batched_modulo += mod()
            batched_modulo += mod(is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out


line_functions = LineFunctions(fq2=fq2_script)

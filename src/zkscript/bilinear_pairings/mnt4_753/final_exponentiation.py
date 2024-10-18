"""final_exponentiation module.

This module enables constructing Bitcoin scripts that perform the final exponentiation in the Ate pairing for MNT4-753.
"""
from tx_engine import Script

from src.zkscript.bilinear_pairings.mnt4_753.fields import fq2_script, fq4_script
from src.zkscript.bilinear_pairings.mnt4_753.parameters import exp_miller_loop
from src.zkscript.bilinear_pairings.model.cyclotomic_exponentiation import CyclotomicExponentiation
from src.zkscript.util.utility_scripts import pick, verify_bottom_constant


class FinalExponentiation(CyclotomicExponentiation):
    """Final exponentiation in the Ate pairing for MNT4-753."""
    def __init__(self, fq2, fq4):
        """Initialise the final exponentiation for MNT4-753.

        Args:
            fq2: The script implementation of the field F_q^2, the quadratic extension of F_q.
            fq4: The script implementation of the field F_q^4, the quadratic extension of F_q^2.
        """
        self.MODULUS = fq4.MODULUS
        self.FQ4 = fq4
        self.cyclotomic_inverse = fq2.negate
        self.square = fq4.square
        self.mul = fq4.mul
        self.EXTENSION_DEGREE = 4

    def easy_exponentiation_with_inverse_check(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Easy part of the final exponentiation.

        Stack input:
            - stack:    [q, ..., inverse(f), f], `f` and `inverse(f)` are elements in F_q^4
            - altstack: []

        Stack output:
            - stack:    [q, ..., f^(q^2-1)],
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, at the end of the execution, q is left as the ???
                element at the top of the stack.

        Returns:
            Script to perform the easy part of the exponentiation in the Ate pairing for MNT4-753.

        Notes:
            The inverse of `f` is passed as input value on the stack and verified during script execution.
        """
        fq4 = self.FQ4

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: Inverse(f) f
        check_f_inverse = pick(position=7, n_elements=4)  # Bring Inverse(f) on top of the stack
        check_f_inverse += pick(position=7, n_elements=4)  # Bring f on top of the stack
        check_f_inverse += fq4.mul(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        check_f_inverse += Script.parse_string(" ".join(["OP_0", "OP_EQUALVERIFY"] * 3))
        check_f_inverse += Script.parse_string("OP_1 OP_EQUALVERIFY")

        # After this, the stack is: Inverse(f) Conjugate(f)
        easy_exponentiation = fq4.frobenius_even(
            n=2, take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute f^(q^2)
        easy_exponentiation += fq4.mul(
            take_modulo=take_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )  # Compute f^(q^2) * Inverse(f)

        out += check_f_inverse + easy_exponentiation

        return out

    def hard_exponentiation(
        self,
        take_modulo: bool,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Hard part of the final exponentiation.

        Stack input:
            - stack:    [q, ..., g], `g` is an element in F_q^4, the quadratic extension of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., g^(q + u + 1)],
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            modulo_threshold (int): The threshold after which we reduce the result with the modulo. Given as bit length.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to perform the hard part of the exponentiation in the Ate pairing for MNT4-753.

        Notes:
            `g` is the output of the easy part of the exponentiation.
        """
        fq4 = self.FQ4

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # After this, the stack is: g, altstack = [g^q]
        out += pick(position=3, n_elements=4)
        out += fq4.frobenius_odd(n=1, take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # After this, the stack is: g g^u, altstack = [g^q]
        out += pick(position=3, n_elements=4)
        out += self.cyclotomic_exponentiation(
            exp_e=exp_miller_loop,
            take_modulo=True,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=False,
        )

        # After this, the stack is: g^[q + u + 1]
        out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 4))
        out += fq4.mul(take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False)
        out += fq4.mul(
            take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
        )

        return out


final_exponentiation = FinalExponentiation(fq2=fq2_script, fq4=fq4_script)

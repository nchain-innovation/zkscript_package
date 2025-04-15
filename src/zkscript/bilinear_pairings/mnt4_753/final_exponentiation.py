"""Bitcoin scripts that perform the final exponentiation in the pairing for MNT4-753."""

from tx_engine import Script

from src.zkscript.bilinear_pairings.mnt4_753.fields import fq2_script, fq4_script
from src.zkscript.bilinear_pairings.mnt4_753.parameters import exp_miller_loop
from src.zkscript.bilinear_pairings.model.cyclotomic_exponentiation import CyclotomicExponentiation
from src.zkscript.fields.fq2 import Fq2
from src.zkscript.fields.fq2_over_2_residue_equal_u import Fq2Over2ResidueEqualU
from src.zkscript.script_types.stack_elements import StackFiniteFieldElement
from src.zkscript.util.utility_scripts import move, pick, roll, verify_bottom_constant


class FinalExponentiation(CyclotomicExponentiation):
    """Final exponentiation in the pairing for MNT4-753.

    Attributes:
        modulus (int): Modulus of the field.
        fq4 (Fq2Over2ResidueEqualU): Instance of the Fq2Over2ResidueEqualU class.
        cyclotomic_inverse (Callable): Function to compute the cyclotomic inverse in Fq4.
        square (Callable): Function to compute the square in Fq4.
        mul (Callable): Function to compute the multiplication in Fq4.
        extension_degree (int): Degree of the field extension. Equal to 4.
    """

    def __init__(self, fq2: Fq2, fq4: Fq2Over2ResidueEqualU):
        """Initialise the final exponentiation for MNT4-753.

        Args:
            fq2 (fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
            fq4 (Fq2Over2ResidueEqualU): Bitcoin script instance to perform arithmetic operations in F_q^4,
                the quadratic extension of F_q^2, built with non residue equal to u.
        """
        self.modulus = fq4.modulus
        self.fq4 = fq4
        self.cyclotomic_inverse = fq2.negate
        self.square = fq4.square
        self.mul = fq4.mul
        self.extension_degree = 4

    def easy_exponentiation_with_inverse_check(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        f_inverse: StackFiniteFieldElement = StackFiniteFieldElement(7, False, 4),  # noqa: B008
        f: StackFiniteFieldElement = StackFiniteFieldElement(3, False, 4),  # noqa: B008
    ) -> Script:
        """Easy part of the final exponentiation.

        Stack input:
            - stack:    [q, ..., inverse(f), ..., f, ...], `f` and `inverse(f)` are elements in F_q^4
            - altstack: []

        Stack output:
            - stack:    [q, ..., g := f^(q^2-1)], `g` is an element in F_q^4
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            f_inverse (StackFiniteFieldElement): the value `f_inverse`. Defaults to
                StackFiniteFieldElement = StackFiniteFieldElement(7, False, 4).
            f (StackFiniteFieldElement): the value `f`. Defaults to
                StackFiniteFieldElement = StackFiniteFieldElement(3, False, 4).

        Returns:
            Script to perform the easy part of the exponentiation in the pairing for MNT4-753.

        Notes:
            The inverse of `f` `inverse(f)` is passed as input value on the stack and verified during script execution.
        """
        is_default_config = (f_inverse.position == self.extension_degree * 2 - 1) and (
            f.position == self.extension_degree - 1
        )

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # After this, the stack is: Inverse(f) f
        if not is_default_config:
            out += move(f_inverse, roll)
            out += move(f.shift(f_inverse.extension_degree * f_inverse.is_before(f)), roll)

        # After this, the stack is: Inverse(f) f
        check_f_inverse = pick(position=7, n_elements=4)  # Bring Inverse(f) on top of the stack
        check_f_inverse += pick(position=7, n_elements=4)  # Bring f on top of the stack
        check_f_inverse += self.fq4.mul(
            take_modulo=True, positive_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        check_f_inverse += Script.parse_string(" ".join(["OP_0", "OP_EQUALVERIFY"] * 3))
        check_f_inverse += Script.parse_string("OP_1 OP_EQUALVERIFY")

        # After this, the stack is: Inverse(f) Conjugate(f)
        easy_exponentiation = self.fq4.frobenius_even(
            n=2, take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute f^(q^2)
        easy_exponentiation += self.fq4.mul(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
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
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Hard part of the final exponentiation.

        Stack input:
            - stack:    [q, ..., g], `g` is an element in F_q^4, the quadratic extension of F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., g^(q + u + 1)]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to perform the hard part of the exponentiation in the pairing for MNT4-753.

        Notes:
            `g` is the output of the easy part of the exponentiation.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # After this, the stack is: g, altstack = [g^q]
        out += pick(position=3, n_elements=4)
        out += self.fq4.frobenius_odd(n=1, take_modulo=False, check_constant=False, clean_constant=False)
        out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 4))

        # After this, the stack is: g g^u, altstack = [g^q]
        out += pick(position=3, n_elements=4)
        out += self.cyclotomic_exponentiation(
            exp_e=exp_miller_loop,
            take_modulo=True,
            positive_modulo=False,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=False,
        )

        # After this, the stack is: g^[q + u + 1]
        out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * 4))
        out += self.fq4.mul(
            take_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            positive_modulo=False,
        )
        out += self.fq4.mul(
            take_modulo=take_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            is_constant_reused=False,
            positive_modulo=positive_modulo,
        )

        return out


final_exponentiation = FinalExponentiation(fq2=fq2_script, fq4=fq4_script)

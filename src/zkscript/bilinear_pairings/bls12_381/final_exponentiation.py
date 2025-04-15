"""Bitcoin scripts that perform the final exponentiation in the pairing for BLS12-381."""

from tx_engine import Script

from src.zkscript.bilinear_pairings.bls12_381.fields import fq12_script, fq12cubic_script
from src.zkscript.bilinear_pairings.bls12_381.parameters import exp_miller_loop
from src.zkscript.bilinear_pairings.model.cyclotomic_exponentiation import CyclotomicExponentiation
from src.zkscript.fields.fq12_2_over_3_over_2 import Fq12
from src.zkscript.script_types.stack_elements import StackFiniteFieldElement
from src.zkscript.util.utility_scripts import move, pick, roll, verify_bottom_constant


class FinalExponentiation(CyclotomicExponentiation):
    """Final exponentiation in the pairing for BLS12-381.

    Attributes:
        modulus (int): Modulus of the field.
        fq12 (Fq12): Bitcoin script instance to perform arithmetic operations in F_q^12, the quadratic extension of
            F_q^6.
        cyclotomic_inverse (function): Cyclotomic inverse function in F_q^12.
        square (function): Square function in F_q^12.
        mul (function): Multiply function in F_q^12.
        extension_degree (int): Extension degree of the field. Equal to 12.
    """

    def __init__(self, fq12: Fq12):
        """Initialise the final exponentiation for BLS12-381.

        Args:
            fq12 (Fq12): Bitcoin script instance to perform arithmetic operations in F_q^12, the quadratic extension of
            F_q^6.
        """
        self.modulus = fq12.modulus
        self.fq12 = fq12
        self.cyclotomic_inverse = fq12.conjugate
        self.square = fq12.square
        self.mul = fq12.mul
        self.extension_degree = 12

    def easy_exponentiation_with_inverse_check(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        f_inverse: StackFiniteFieldElement = StackFiniteFieldElement(23, False, 12),  # noqa: B008
        f: StackFiniteFieldElement = StackFiniteFieldElement(11, False, 12),  # noqa: B008
    ) -> Script:
        """Easy part of the final exponentiation.

        Stack input:
            - stack:    [q, ..., inverse(f_quadratic), ..., f, ...], `f` is an element in F_q^12, the cubic extension of
                F_q^4, `f_quadratic` is the same element in the quadratic extension of F_q^6, and its inverse is also an
                element in the quadratic extension of F_q^6
            - altstack: []

        Stack output:
            - stack:    [q, ..., g := f^[(q^6-1)(q^2+1)]], `g` is an element in F_q^12, the quadratic extension of F_q^6
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            f_inverse (StackFiniteFieldElement): the value `f_inverse`. Defaults to
                StackFiniteFieldElement = StackFiniteFieldElement(23, False, 12).
            f (StackFiniteFieldElement): the value `f`. Defaults to
                StackFiniteFieldElement = StackFiniteFieldElement(11, False, 12).

        Returns:
            Script to perform the easy part of the exponentiation in the pairing for BLS12-381.

        Notes:
            The inverse of `f` `inverse(f_quadratic)` is passed as input value on the stack and verified during script
            execution.
        """
        is_default_config = (f_inverse.position == self.extension_degree * 2 - 1) and (
            f.position == self.extension_degree - 1
        )

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # After this, the stack is: Inverse(f_quadratic) f
        if not is_default_config:
            out += move(f_inverse, roll)
            out += move(f.shift(f_inverse.extension_degree * f_inverse.is_before(f)), roll)

        # After this, the stack is: Inverse(f_quadratic) f_quadratic
        check_f_inverse = pick(position=23, n_elements=12)  # Bring Inverse(f_quadratic) on top of the stack
        check_f_inverse += pick(position=23, n_elements=12)  # Bring f_quadratic on top of the stack
        check_f_inverse += self.fq12.mul(
            take_modulo=True, positive_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Multiply
        check_f_inverse += Script.parse_string(" ".join(["OP_0", "OP_EQUALVERIFY"] * 11))
        check_f_inverse += Script.parse_string("OP_1 OP_EQUALVERIFY")

        # After this, the stack is: Inverse(f_quadratic) Conjugate(f_quadratic)
        # Conjugate f_quadratic
        easy_exponentiation = self.fq12.conjugate(take_modulo=False, check_constant=False, clean_constant=False)
        # Compute Inverse(f_quadratic) * Conjugate(f_quadratic)
        easy_exponentiation += self.fq12.mul(take_modulo=False, check_constant=False, clean_constant=False)
        # Duplicate Inverse(f_quadratic) * Conjugate(f_quadratic)
        easy_exponentiation += pick(position=11, n_elements=12)
        # Compute (Inverse(f_quadratic) * Conjugate(f_quadratic))^(q^2)
        easy_exponentiation += self.fq12.frobenius_even(
            n=2, take_modulo=False, check_constant=False, clean_constant=False
        )
        easy_exponentiation += self.fq12.mul(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            is_constant_reused=is_constant_reused,
        )

        # The output of the Miller loop in this implementation of BLS12_381 is in Fq12Cubic, so we need to turn it to
        # its quadratic version
        out += fq12cubic_script.to_quadratic()
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
            - stack:    [q, ..., g], `g` is an element in F_q^12, the quadratic extension of F_q^6
            - altstack: []

        Stack output:
            - stack:    [q, ..., g^[(q^4 - q^2 + 1)/r]]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to perform the hard part of the exponentiation in the pairing for BLS12-381.

        Notes:
            - `g` is the output of the easy part of the exponentiation.
            - `gammas` is a dictionary where `gammas['i']` are the gammas required for Frobenius applied `i` times.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Step 1
        # After this, the stack is g t0
        out += pick(position=11, n_elements=12)
        out += self.fq12.square(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )

        # Step 2
        # After this, the stack is g t0 t1
        out += pick(position=11, n_elements=12)  # Duplicate t0
        out += self.cyclotomic_exponentiation(
            exp_e=exp_miller_loop,
            take_modulo=True,
            positive_modulo=False,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=False,
        )  # Compute t1

        # Step 3
        # After this, the stack is g t0 t1 t2
        out += pick(position=11, n_elements=12)  # Duplicate t1
        out += self.cyclotomic_exponentiation(
            exp_e=exp_miller_loop[1:],
            take_modulo=True,
            positive_modulo=False,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=False,
        )  # Compute t2

        # Step 4
        # After this, the stack is g t0 t1 t2 t3
        out += pick(position=47, n_elements=12)  # Pick g
        out += self.fq12.conjugate(take_modulo=False, check_constant=False, clean_constant=False)  # Compute t3
        # Step 5
        # After this, the stack is: g t0 t2 t1
        out += roll(position=35, n_elements=12)  # Roll t1
        out += self.fq12.mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute t1 * t3

        # Step 6
        # After this, the stack is g t0 t2 t1
        out += self.fq12.conjugate(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute Conjugate(t1)

        # Step 7
        # After this, the stack is g t0 t1
        out += self.fq12.mul(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute t1 * t2

        # Step 8
        # After this, the stack is g t0 t1 t2
        out += pick(position=11, n_elements=12)  # Duplicate t1
        out += self.cyclotomic_exponentiation(
            exp_e=exp_miller_loop,
            take_modulo=True,
            positive_modulo=False,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=False,
        )  # Compute t2

        # Step 9
        # After this, the stack is g t0 t1 t2 t3
        out += pick(position=11, n_elements=12)  # Duplicate t2
        out += self.cyclotomic_exponentiation(
            exp_e=exp_miller_loop,
            take_modulo=True,
            positive_modulo=False,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=False,
        )  # Compute t3

        # Step 10
        # After this, the stack is g t0 t1 t2 t3 Conjugate(t1)
        out += pick(position=35, n_elements=12)  # Pick t1
        out += self.fq12.conjugate(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute Conjugate(t1)

        # Step 11
        # After this, the stack is g t0 t1 t2 t3
        out += self.fq12.mul(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute t3 * Conjugate(t1)

        # Step 12 - 13
        # After this, the stack is: g t0 t2 t3 t1
        out += roll(position=35, n_elements=12)  # Roll t1
        out += self.fq12.frobenius_odd(
            n=3, take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute t1^(q^3)

        # Step 14
        # After this, the stack is: g t0 t3 t1 t2
        out += roll(position=35, n_elements=12)  # Roll t2
        out += self.fq12.frobenius_even(
            n=2, take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute t2^(q^2)

        # Step 15
        # After this, the stack is: g t0 t3 t1
        out += self.fq12.mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute t1 * t2

        # Step 16
        # After this, the stack is: g t0 t3 t1 t2
        out += pick(position=23, n_elements=12)  # Pick t3
        out += self.cyclotomic_exponentiation(
            exp_e=exp_miller_loop,
            take_modulo=True,
            positive_modulo=False,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=False,
        )  # Compute t3^u

        # Step 17
        # After this, the stack is: g t3 t1 t2
        out += roll(position=47, n_elements=12)  # Roll t0
        out += self.fq12.mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute t2 * t0

        # Step 18
        # After this, the stack is: t3 t1 t2
        out += roll(position=47, n_elements=12)  # Roll g
        out += self.fq12.mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute t2 * g

        # Step 19
        # After this, the stack is: t3 t1
        out += self.fq12.mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute t1 * t2

        # Step 20
        # After this, the stack is: t1 t2
        out += roll(position=23, n_elements=12)  # Roll t3
        out += self.fq12.frobenius_odd(
            n=1, take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute t3^q

        # Step 21
        # After this, the stack is: g^[(q^4 - q^2 + 1)/r]
        out += self.fq12.mul(
            take_modulo=take_modulo,
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            is_constant_reused=False,
        )

        return out


final_exponentiation = FinalExponentiation(fq12=fq12_script)

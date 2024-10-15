# Final exponentiation for MNT4_753

from tx_engine import Script

from src.zkscript.bilinear_pairings.mnt4_753.fields import fq2_script, fq4_script
from src.zkscript.bilinear_pairings.mnt4_753.parameters import exp_miller_loop
from src.zkscript.bilinear_pairings.model.cyclotomic_exponentiation import CyclotomicExponentiation
from src.zkscript.util.utility_scripts import pick, verify_bottom_constant


class FinalExponentiation(CyclotomicExponentiation):
    def __init__(self, fq2, fq4):
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
        """Easy part of the exponentiation with inverse calculated off-chain and verified during the script execution.

        Input:
            - Inverse(f) f
        Output:
            - f^[(q^2-1]
        Assumption of data:
            - f and Inverse(f) are passed as couples of elements in Fq2
        """
        # Fq4 implementation
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
        """Hard part of the exponentation.

        Input:
            - g (output of the easy part)
        Output:
            - g^[q + u + 1]
        Assumption on data:
            - g is passed as a couple of elements in Fq2
        """
        # Fq4 implementation
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

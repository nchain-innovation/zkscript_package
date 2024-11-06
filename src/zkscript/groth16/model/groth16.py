"""Bitcoin scripts that perform Groth16 proof verification."""

from math import log2

from tx_engine import Script

# Pairing
from src.zkscript.bilinear_pairings.model.model_definition import PairingModel

# Script implementations
# EC arithmetic
from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.elliptic_curves.ec_operations_fq_unrolled import EllipticCurveFqUnrolled
from src.zkscript.types.locking_keys.groth16 import Groth16LockingKey
from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import nums_to_script, roll, verify_bottom_constant


class Groth16(PairingModel):
    """Groth16 class.

    Attributes:
        pairing_model: Pairing model used to instantiate Groth16.
        curve_a (int): A coefficient of the base curve over which Groth16 is instantiated.
        r (int): The order of G1/G2/GT.
    """

    def __init__(self, pairing_model, curve_a: int, r: int):
        """Initialise the Groth16 class.

        Args:
            pairing_model: Pairing model used to instantiate Groth16.
            curve_a (int): A coefficient of the base curve over which Groth16 is instantiated.
            r (int): The order of G1/G2/GT.
        """
        self.pairing_model = pairing_model
        self.curve_a = curve_a
        self.r = r

    def groth16_verifier(
        self,
        locking_key: Groth16LockingKey,
        modulo_threshold: int,
        max_multipliers: list[int] | None = None,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Groth16 verifier.

        Stack input:
            - stack:    [q, ..., inverse_miller_loop_triple_pairing, lambdas_pairing, A, B, C,
                lambda[sum_(i=0)^(l-1), a_i * gamma_abc[i], a_l * gamma_abc[l]], ..., lambda[gamma_abc[0],
                a_1 * gamma_abc[1]], a_1, lambdas[a_1,gamma_abc[1]], ..., a_l, lambdas[a_l,gamma_abc[l]]]

                where:
                 - a_i lambdas[a_i,gamma_abc[i]] is the input required to execute unrolled_multiplication from
                    EllipticCurveFqUnrolled (except for gamma_abc[i], which is hard coded into the script)
                - lambda[sum_(i=0)^(j-1) a_i * gamma_abc[i], a_j * gamma_abc[j]] is the gradient through
                    a_j * gamma_abc[j] and sum_(i=0)^(j-1) a_i * gamma_abc[i] to compute their sum
                - lambdas_pairing are the lambdas needed to execute the function self.triple_pairing() (from the Pairing
                    class) to compute the triple pairing
            - altstack: []

        Stack output:
            - stack:    [q, ..., True/False]
            - altstack: []

        Args:
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            alpha_beta (list[int]): List of integers representing the alpha and beta coefficients for the computation.
            minus_gamma (list[int]): List of integers representing the negated gamma values for the computation.
            minus_delta (list[int]): List of integers representing the negated delta values for the computation
            gamma_abc (list[list[int]]): List of points given in the Common Reference String.
            max_multipliers (list[int]): List where each element max_multipliers[i] is the max value of the i-th public
                statement.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to verify the equation e(A,B) = alpha_beta * e(sum_(i=0)^(l) a_i * gamma_abc[i], gamma) * e(C, delta)
            which we turn into  e(A,B) * e(sum_(i=0)^(l) a_i * gamma_abc[i], - gamma) * e(C, - delta) = alpha_beta.
            The LHS of the equation is a triple pairing defined in bilinear_pairings/model/triple_pairing.py

        Notes:
            a_0 = 1.
        """
        n_pub = len(locking_key.gamma_abc) - 1

        # Elliptic curve arithmetic
        ec_fq = EllipticCurveFq(q=self.pairing_model.MODULUS, curve_a=self.curve_a)
        # Unrolled EC arithmetic
        ec_fq_unrolled = EllipticCurveFqUnrolled(q=self.pairing_model.MODULUS, ec_over_fq=ec_fq)

        out = verify_bottom_constant(self.pairing_model.MODULUS) if check_constant else Script()

        """
        After this:
            - the stack is: q .. inverse_miller_loop_triple_pairing lambdas_pairing A B C
            lambda[sum_(i=0)^(l-1) a_i * gamma_abc[i], a_l * gamma_abc[l]] ..
            lambda[gamma_abc[0], a_1 * gamma_abc[1]] gamma_abc[0]
            - the altstack: a_l * gamma_abc[l] ... a_1 * gamma_abc[1]
        """
        for i in range(n_pub, -1, -1):
            # After this, the top of the stack is: a_(i-1) lambdas[a_(i-1),gamma_abc[i-1]],
            # altstack = [..., a_i * gamma_abc[i]]
            if not any(locking_key.gamma_abc[i]):
                out += Script.parse_string(" ".join(["0x00"] * self.pairing_model.N_POINTS_CURVE))
            else:
                out += nums_to_script(locking_key.gamma_abc[i])
            if i > 0:
                max_multiplier = self.r if max_multipliers is None else max_multipliers[i - 1]
                out += ec_fq_unrolled.unrolled_multiplication(
                    max_multiplier=max_multiplier,
                    modulo_threshold=modulo_threshold,
                    check_constant=False,
                    clean_constant=False,
                    positive_modulo=False,
                )
                out += Script.parse_string("OP_2SWAP OP_2DROP")  # Drop gamma_abc[i]
                out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * self.pairing_model.N_POINTS_CURVE))

        # After this, the stack is: q .. lambdas_pairing inverse_miller_loop_triple_pairing A B C
        # sum_(i=0)^l a_i * gamma_abc[i]
        for _i in range(n_pub):
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * self.pairing_model.N_POINTS_CURVE))
            out += ec_fq.point_addition_with_unknown_points(
                take_modulo=True, positive_modulo=False, check_constant=False, clean_constant=False
            )

        # After this, the stack is: q .. lambdas_pairing inverse_miller_loop_triple_pairing A
        # sum_(i=0)^l a_i * gamma_abc[i] C B gamma delta
        out += roll(
            position=2 * self.pairing_model.N_POINTS_CURVE - 1, n_elements=self.pairing_model.N_POINTS_CURVE
        )  # Roll C
        out += roll(
            position=2 * self.pairing_model.N_POINTS_CURVE + self.pairing_model.N_POINTS_TWIST - 1,
            n_elements=self.pairing_model.N_POINTS_TWIST,
        )  # Roll B
        out += nums_to_script(locking_key.minus_gamma)
        out += nums_to_script(locking_key.minus_delta)

        # After this, the stack is: q .. e(A,B) * e(sum_(i=0)^(l) a_i * gamma_abc[i], gamma) * e(C, delta)
        out += self.pairing_model.triple_pairing(
            modulo_threshold=modulo_threshold, check_constant=False, clean_constant=clean_constant
        )

        # After this, the top of the stack is:
        # [e(A,B) * e(sum_(i=0)^(l) a_i * gamma_abc[i], gamma) * e(C, delta) ?= alpha_beta]
        for ix, el in enumerate(locking_key.alpha_beta[::-1]):
            out += nums_to_script([el])
            if ix != len(locking_key.alpha_beta) - 1:
                out += Script.parse_string("OP_EQUALVERIFY")
            else:
                out += Script.parse_string("OP_EQUAL")

        return optimise_script(out)

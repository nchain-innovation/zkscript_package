"""Bitcoin scripts that perform Groth16 proof verification."""

from tx_engine import Script, encode_num, hash256d

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

    def __gradients_to_hash_commitment(self, locking_key: Groth16LockingKey) -> bytes:
        """Construct the hash commitment for the gradients of -gamma and -delta.

        Args:
            locking_key (Groth16LockingKey): Locking key used to generate the verifier. Encapsulates the data of the
                CRS needed by the verifier.
        """
        verification_hash = b""
        for i in range(len(locking_key.gradients_pairings[0])):
            for j in range(len(locking_key.gradients_pairings[0][i])):
                for k in range(2,0,-1):
                    for s in range(self.pairing_model.EXTENSION_DEGREE - 1, -1, -1):
                        verification_hash = encode_num(locking_key.gradients_pairings[k][i][j][s]) + verification_hash
                        verification_hash = hash256d(verification_hash)
        return verification_hash

    def __verify_hash_commitment(self, locking_key: Groth16LockingKey, verification_hash: bytes) -> Script:
        """Script that verifies that the gradients contained in `locking_key` commit to verification_hash.

        Stack input:
            - stack: [.., gradients_pairing]

        Stack output:
            - stack: [.., ] or fail

        Args:
            locking_key (Groth16LockingKey): Locking key used to generate the verifier. Encapsulates the data of the
                CRS needed by the verifier.
            verification_hash (bytes): The hash commitment against which we verify the gradients contained in
                `locking_key`.
        """
        list_of_opcodes = []
        for i in range(len(locking_key.gradients_pairings[0]) - 1, -1, -1):
            for _ in range(len(locking_key.gradients_pairings[0][i]) - 1, -1, -1):
                for _ in range(1, 3):
                    for _ in range(self.pairing_model.EXTENSION_DEGREE):
                        list_of_opcodes.append("OP_HASH256")
                        list_of_opcodes.append("OP_CAT")
        del list_of_opcodes[-1]
        string_of_opcodes = " ".join(list_of_opcodes)
        out = Script.parse_string(string_of_opcodes)
        out.append_pushdata(verification_hash)
        out += Script.parse_string("OP_EQUAL")
        return out

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
            - stack:    [q, ..., inverse_miller_loop_triple_pairing, gradients_pairing, A, B, C,
                gradient[sum_(i=0)^(l-1), a_i * gamma_abc[i], a_l * gamma_abc[l]], ..., gradient[gamma_abc[0],
                a_1 * gamma_abc[1]], a_1, gradients[a_1,gamma_abc[1]], ..., a_l, gradients[a_l,gamma_abc[l]]]

                where:
                 - a_i gradients[a_i,gamma_abc[i]] is the input required to execute unrolled_multiplication from
                    EllipticCurveFqUnrolled (except for gamma_abc[i], which is hard coded into the script)
                - gradient[sum_(i=0)^(j-1) a_i * gamma_abc[i], a_j * gamma_abc[j]] is the gradient through
                    a_j * gamma_abc[j] and sum_(i=0)^(j-1) a_i * gamma_abc[i] to compute their sum
                - gradients_pairing are the gradients needed to execute the method `self.triple_pairing()`
                    (from the Pairing class) to compute the triple pairing
            - altstack: []

        Stack output:
            - stack:    [q, ..., True/False]
            - altstack: []

        Args:
            locking_key (Groth16LockingKey): Locking key used to generate the verifier. Encapsulates the data of the
                CRS needed by the verifier.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
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
        # Hash used to verify the gradients of -gamma and -delta
        verification_hash = self.__gradients_to_hash_commitment(locking_key=locking_key)

        out = verify_bottom_constant(self.pairing_model.MODULUS) if check_constant else Script()

        for i in range(n_pub, -1, -1):
            # stack in:     [q, ..., inverse_miller_loop_triple_pairing, gradients_pairing, A, B, C,
            #                   gradient[sum_(i=0)^(l-1), a_i * gamma_abc[i], a_l * gamma_abc[l]], ...,
            #                       gradient[gamma_abc[0], a_1 * gamma_abc[1]], a_1, gradients[a_1,gamma_abc[1]], ...,
            #                           a_l, gradients[a_l,gamma_abc[l]]]
            # stack out:    [q, ..., inverse_miller_loop_triple_pairing, gradients_pairing, A, B, C,
            #                   gradient[sum_(i=0)^(l-1), a_i * gamma_abc[i], a_l * gamma_abc[l]], ...,
            #                       gradient[gamma_abc[0], a_1 * gamma_abc[1]], gamma_abc[0]]
            # altstack out: [a[l] * gamma_abc[l], .., a[1] * gamma_abc[1]]
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

        # stack in:     [q, ..., inverse_miller_loop_triple_pairing, gradients_pairing, A, B, C,
        #                   gradient[sum_(i=0)^(l-1), a_i * gamma_abc[i], a_l * gamma_abc[l]], ...,
        #                       gradient[gamma_abc[0], a_1 * gamma_abc[1]], gamma_abc[0]]
        # altstack in:  [a[l] * gamma_abc[l], .., a[1] * gamma_abc[1]]
        # stack out:    [q, ..., inverse_miller_loop_triple_pairing, gradients_pairing, A, B, C,
        #                   sum_(i=0)^l a_i * gamma_abc[i]]
        # altstack out: []
        for _ in range(n_pub):
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * self.pairing_model.N_POINTS_CURVE))
            out += ec_fq.point_addition_with_unknown_points(
                take_modulo=True, positive_modulo=False, check_constant=False, clean_constant=False
            )

        # stack in:  [q, ..., inverse_miller_loop_triple_pairing, gradients_pairing, A, B, C,
        #                   sum_(i=0)^l a_i * gamma_abc[i]]
        # stack out: [q, ..., inverse_miller_loop_triple_pairing, gradients_pairing, A,
        #                   sum_(i=0)^l a_i * gamma_abc[i], C, B, -gamma, -delta]
        out += roll(
            position=2 * self.pairing_model.N_POINTS_CURVE - 1, n_elements=self.pairing_model.N_POINTS_CURVE
        )  # Roll C
        out += roll(
            position=2 * self.pairing_model.N_POINTS_CURVE + self.pairing_model.N_POINTS_TWIST - 1,
            n_elements=self.pairing_model.N_POINTS_TWIST,
        )  # Roll B
        out += nums_to_script(locking_key.minus_gamma)
        out += nums_to_script(locking_key.minus_delta)

        # Compute the triple pairing
        # stack in:  [q, ..., inverse_miller_loop_triple_pairing, gradients_pairing, A,
        #                   sum_(i=0)^l a_i * gamma_abc[i], C, B, -gamma, -delta]
        # stack out: [q, ..., gradients_pairing,
        #                   pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta)]
        out += self.pairing_model.triple_pairing(
            modulo_threshold=modulo_threshold,
            positive_modulo=True,
            verify_gradients=(True, False, False),
            check_constant=False,
            clean_constant=clean_constant,
        )

        # Verify pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta) == alpha_beta
        # stack in:  [q, ..., gradients_pairing,
        #                   pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta)]
        # stack out: [q, ..., gradients_pairing] or fail
        for el in locking_key.alpha_beta[::-1]:
            out += nums_to_script([el])
            out += Script.parse_string("OP_EQUALVERIFY")

        # Verify that the gradients supplied for -gamma and -delta are the correct one
        # stack in:  [q, ..., gradients_pairing]
        # stack out: [q, ...] or fail
        out += self.__verify_hash_commitment(locking_key=locking_key, verification_hash=verification_hash)

        return optimise_script(out)

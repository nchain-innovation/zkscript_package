"""Bitcoin scripts that perform Groth16 proof verification."""

from tx_engine import Script, encode_num, hash256d

from src.zkscript.bilinear_pairings.model.model_definition import PairingModel

# Pairing
# Script implementations
# EC arithmetic
from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.elliptic_curves.ec_operations_fq_projective import EllipticCurveFqProjective
from src.zkscript.script_types.locking_keys.groth16 import Groth16LockingKey, Groth16LockingKeyWithPrecomputedMsm
from src.zkscript.script_types.locking_keys.groth16_proj import (
    Groth16ProjLockingKey,
    Groth16ProjLockingKeyWithPrecomputedMsm,
)
from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import nums_to_script, roll, verify_bottom_constant


class Groth16:
    """Groth16 class.

    Attributes:
        pairing_model: Pairing model used to instantiate Groth16.
        curve_a (int): A coefficient of the base curve over which Groth16 is instantiated.
        r (int): The order of G1/G2/GT.
    """

    def __init__(self, pairing_model: PairingModel, curve_a: int, curve_b: int, r: int):
        """Initialise the Groth16 class.

        Args:
            pairing_model (PairingModel): Pairing model used to instantiate Groth16.
            curve_a (int): A coefficient of the base curve over which Groth16 is instantiated.
            curve_b (int): B coefficient of the base curve over which Groth16 is instantiated.
            r (int): The order of G1/G2/GT.
        """
        self.pairing_model = pairing_model
        self.curve_a = curve_a
        self.curve_b = curve_b
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
                for k in range(1, -1, -1):
                    for s in range(self.pairing_model.extension_degree - 1, -1, -1):
                        verification_hash = encode_num(locking_key.gradients_pairings[k][i][j][s]) + verification_hash
                        verification_hash = hash256d(verification_hash)
        return verification_hash

    def __verify_hash_commitment(self, locking_key: Groth16LockingKey, verification_hash: bytes) -> Script:
        """Script that verifies that the gradients contained in `locking_key` commit to verification_hash.

        Stack input:
            - stack: [.., gradients_pairing]

        Stack output:
            - stack: [.., 0/1]

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
                    for _ in range(self.pairing_model.extension_degree):
                        list_of_opcodes.append("OP_HASH256")
                        list_of_opcodes.append("OP_CAT")
        string_of_opcodes = " ".join(list_of_opcodes[:-1])
        out = Script.parse_string(string_of_opcodes)
        out.append_pushdata(verification_hash)
        out += Script.parse_string("OP_EQUAL")
        return out

    def groth16_verifier(
        self,
        locking_key: Groth16LockingKey,
        modulo_threshold: int,
        extractable_inputs: int = 0,
        max_multipliers: list[int] | None = None,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Groth16 verifier.

        Stack input:
            - stack:    [q, ..., inverse_miller_loop_triple_pairing,
                            (gradients_pairing if not locking_key.has_precomputed_gradients), A, B, C,
                                gradient[gamma_abc[0], sum_(i=1)^l a_i * gamma_abc[i]],
                                    gradient[sum_(i=1)^(l-1) a_i * gamma_abc[i], a_1 * gamma_abc[1]], ...,
                                        gradient[a_(l-1) * gamma_abc[l-1], a_l * gamma_abc[l]],
                                            a_2, gradients[a_2,gamma_abc[l]], ..., a_1, gradients[a_1,gamma_abc[1]]]

                where:
                - [a_i, gradients[a_i,gamma_abc[i]]] is the input required to execute `unrolled_multiplication` from
                    EllipticCurveFqUnrolled (except for gamma_abc[i], which is hard coded into the script)
                - gradient[sum_(i=1)^(j-1) a_i * gamma_abc[i], a_j * gamma_abc[j]] is the gradient through
                    a_j * gamma_abc[j] and sum_(i=1)^(j-1) a_i * gamma_abc[i] to compute their sum
                - gradients_pairing are the gradients needed to execute the method `self.triple_pairing()`
                    (from the Pairing class) to compute the triple pairing. These may not be on the stack based on
                    the value of `locking_key.has_precomputed_gradients`.
            - altstack: []

        Stack output:
            - stack:    [q, ..., True/False]
            - altstack: []

        Args:
            locking_key (Groth16LockingKey): Locking key used to generate the verifier. Encapsulates the data of the
                CRS needed by the verifier.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            extractable_inputs (int): The number of public inputs which should be extractable in script.
                Defaults to `0`.
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
        max_multipliers = (
            max_multipliers if max_multipliers is not None else [self.r] * (len(locking_key.gamma_abc) - 1)
        )

        # Elliptic curve arithmetic
        ec_fq = EllipticCurveFq(q=self.pairing_model.modulus, curve_a=self.curve_a, curve_b=self.curve_b)

        out = verify_bottom_constant(self.pairing_model.modulus) if check_constant else Script()

        # stack in:     [q, ..., inverse_miller_loop_triple_pairing,
        #                   (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                       A, B, C, gradient[gamma_abc[0], sum_(i=1)^l a_i * gamma_abc[i]],
        #                       gradient[sum_(i=1)^(l-1) a_i * gamma_abc[i], a_1 * gamma_abc[1]], ...,
        #                           gradient[a_(l-1) * gamma_abc[l-1], a_l * gamma_abc[l]],
        #                               a_2, gradients[a_2,gamma_abc[l]], ..., a_1, gradients[a_1,gamma_abc[1]],
        # stack out:    [q, ..., inverse_miller_loop_triple_pairing,
        #                   (gradients_pairing if not locking_key.has_precomputed_gradients), A, B, C,
        #                       gradient[gamma_abc[0], sum_(i=1)^l a_i * gamma_abc[i]],
        #                           sum_(i=1)^l a_i * gamma_abc[i]]
        out += ec_fq.msm_with_fixed_bases(
            bases=locking_key.gamma_abc[1:],
            max_multipliers=max_multipliers,
            modulo_threshold=modulo_threshold,
            take_modulo=False,
            check_constant=False,
            clean_constant=False,
            positive_modulo=False,
            extractable_scalars=extractable_inputs,
        )

        # Load gamma_abc[0] to the stack
        out += nums_to_script(locking_key.gamma_abc[0])

        # stack in:    [q, ..., inverse_miller_loop_triple_pairing,
        #                  (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                      A, B, C, gradient[gamma_abc[0], sum_(i=1)^l a_i * gamma_abc[i]],
        #                          sum_(i=1)^l a_i * gamma_abc[i]]
        # stack out:   [q, ..., inverse_miller_loop_triple_pairing,
        #                  (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                      A, B, C, sum_(i=0)^l a_i * gamma_abc[i]]
        out += ec_fq.point_addition_with_unknown_points(
            take_modulo=True, positive_modulo=False, check_constant=False, clean_constant=False
        )

        # stack in:    [q, ..., inverse_miller_loop_triple_pairing,
        #                  (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                      A, B, C, sum_(i=0)^l a_i * gamma_abc[i]]
        # stack out: [q, ..., 0/1]
        out += self.groth16_verifier_with_precomputed_msm(
            locking_key=locking_key,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=clean_constant,
        )

        return optimise_script(out)

    def groth16_verifier_with_precomputed_msm(
        self,
        locking_key: Groth16LockingKeyWithPrecomputedMsm,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Groth16 verifier.

        Stack input:
            - stack:    [q, ..., inverse_miller_loop_triple_pairing,
                            (gradients_pairing if not locking_key.has_precomputed_gradients),
                                A, B, C, sum_(i=0)^l a_i * gamma_abc[i]]
                where:
                - gradients_pairing are the gradients needed to execute the method `self.triple_pairing()`
                    (from the Pairing class) to compute the triple pairing. If `locking_key.has_precomputed_gradients`
                    is `False`, these are already on the stack, and are verified at the end of the script. If `True`,
                    they are injected during the execution of the triple pairing.
            - altstack: []

        Stack output:
            - stack:    [q, ..., True/False]
            - altstack: []

        Args:
            locking_key (Groth16LockingKey): Locking key used to generate the verifier. Encapsulates the data of the
                CRS needed by the verifier.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to verify the equation e(A,B) = alpha_beta * e(sum_(i=0)^(l) a_i * gamma_abc[i], gamma) * e(C, delta)
            which we turn into  e(A,B) * e(sum_(i=0)^(l) a_i * gamma_abc[i], - gamma) * e(C, - delta) = alpha_beta.
            The LHS of the equation is a triple pairing defined in bilinear_pairings/model/triple_pairing.py

        Notes:
            a_0 = 1.
        """
        out = verify_bottom_constant(self.pairing_model.modulus) if check_constant else Script()

        # stack in:  [q, ..., inverse_miller_loop_triple_pairing,
        #                (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                    A, B, C, sum_(i=0)^l a_i * gamma_abc[i]]
        # stack out: [q, ..., inverse_miller_loop_triple_pairing,
        #                (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                    A, sum_(i=0)^l a_i * gamma_abc[i], C, B, -gamma, -delta]
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
        # stack in:  [q, ..., inverse_miller_loop_triple_pairing,
        #                (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                    A, sum_(i=0)^l a_i * gamma_abc[i], C, B, -gamma, -delta]
        # altstack in: [(gradients_pairing if locking_key.has_precomputed_gradients)]
        # stack out: [q, ..., (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                   pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta)]
        out += self.pairing_model.triple_pairing(
            modulo_threshold=modulo_threshold,
            positive_modulo=True,
            verify_gradients=(True, False, False),
            check_constant=False,
            clean_constant=clean_constant,
            is_precomputed_gradients_on_stack=not locking_key.has_precomputed_gradients,
            precomputed_gradients=locking_key.gradients_pairings,
        )

        # Verify pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta) == alpha_beta
        # stack in:  [q, ..., (gradients_pairing if not locking_key.has_precomputed_gradients),
        #                   pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta)]
        # stack out: [q, ..., 0/1] if locking_key.has_precomputed_gradients else ([q, ..., gradients_pairing] or fail)
        for i, el in enumerate(locking_key.alpha_beta[::-1]):
            out += nums_to_script([el])
            out += (
                Script.parse_string("OP_EQUAL")
                if locking_key.has_precomputed_gradients and i == len(locking_key.alpha_beta) - 1
                else Script.parse_string("OP_EQUALVERIFY")
            )

        # If locking_key.has_precomputed_gradients is False, verify that the gradients supplied by the unlocking script
        # for -gamma and -delta are the correct ones.
        # stack in:  [q, ..., gradients_pairing] if not locking_key.has_precomputed_gradients
        # stack out: [q, ..., 0/1]
        if not locking_key.has_precomputed_gradients:
            # Hash used to verify the gradients of -gamma and -delta
            verification_hash = self.__gradients_to_hash_commitment(locking_key=locking_key)
            out += self.__verify_hash_commitment(locking_key=locking_key, verification_hash=verification_hash)

        return optimise_script(out)

    def groth16_verifier_proj(
        self,
        locking_key: Groth16ProjLockingKey,
        modulo_threshold: int,
        extractable_inputs: int = 0,
        max_multipliers: list[int] | None = None,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Groth16 verifier with projective coordinates.

        Stack input:
            - stack:    [q, ..., inverse_miller_loop_triple_pairing, A, B, C, ..., a_i, ..., a_1]
            - altstack: []

        Stack output:
            - stack:    [q, ..., True/False]
            - altstack: []

        Args:
            locking_key (Groth16ProjLockingKey): Locking key used to generate the verifier. Contains the data of the
                CRS needed by the verifier.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            extractable_inputs (int): The number of public inputs which should be extractable in script.
                Defaults to `0`.
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
        max_multipliers = (
            max_multipliers if max_multipliers is not None else [self.r] * (len(locking_key.gamma_abc) - 1)
        )

        # Elliptic curve arithmetic
        ec_fq = EllipticCurveFqProjective(q=self.pairing_model.modulus, curve_a=self.curve_a, curve_b=self.curve_b)

        out = verify_bottom_constant(self.pairing_model.modulus) if check_constant else Script()

        # stack in:     [q, ..., inverse_miller_loop_triple_pairing, A, B, C, ..., a_2, a_1],
        # stack out:    [q, ..., inverse_miller_loop_triple_pairing, A, B, C, sum_(i=0)^l a_i * gamma_abc[i]]
        out += ec_fq.msm_with_fixed_bases(
            bases=locking_key.gamma_abc[1:],
            max_multipliers=max_multipliers,
            take_modulo=True,
            check_constant=False,
            clean_constant=False,
            positive_modulo=False,
            extractable_scalars=extractable_inputs,
        )

        # Load gamma_abc[0] to the stack
        out += nums_to_script(locking_key.gamma_abc[0])

        # if gamma_abc[0] is affine, it is mapped to
        if len(locking_key.gamma_abc[0]) == 2:  # noqa PLR2004
            out += Script.parse_string("OP_1")

        # Sum gamma_abc[0] (a_0 = 1)
        out += ec_fq.point_addition_with_unknown_points(
            take_modulo=True, positive_modulo=False, check_constant=False, clean_constant=False
        )

        # Convert sum_(i=0)^l a_i * gamma_abc[i] in affine coordinates
        # Compute the inverse of the z coordinate
        out += self.pairing_model.inverse_fq(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            rolling_option=1,
            mod_frequency=modulo_threshold // (self.pairing_model.modulus.bit_length() * 3 + 3),
        )
        # Multiply x and y for z^-1
        out += Script.parse_string("OP_TUCK OP_MUL OP_TOALTSTACK OP_MUL OP_FROMALTSTACK")

        # stack in:    [q, ..., inverse_miller_loop_triple_pairing, A, B, C, sum_(i=0)^l a_i * gamma_abc[i]]
        # stack out: [q, ..., 0/1]
        out += self.groth16_verifier_proj_with_precomputed_msm(
            locking_key=locking_key,
            modulo_threshold=modulo_threshold,
            check_constant=False,
            clean_constant=clean_constant,
        )

        return optimise_script(out)

    def groth16_verifier_proj_with_precomputed_msm(
        self,
        locking_key: Groth16ProjLockingKeyWithPrecomputedMsm,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Groth16 verifier.

        Stack input:
            - stack:    [q, ..., inverse_miller_loop_triple_pairing, A, B, C, sum_(i=0)^l a_i * gamma_abc[i]]
            - altstack: []

        Stack output:
            - stack:    [q, ..., True/False]
            - altstack: []

        Args:
            locking_key (Groth16ProjLockingKey): Locking key used to generate the verifier. Contains the data of the
                CRS needed by the verifier.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to verify the equation e(A,B) = alpha_beta * e(sum_(i=0)^(l) a_i * gamma_abc[i], gamma) * e(C, delta)
            which we turn into  e(A,B) * e(sum_(i=0)^(l) a_i * gamma_abc[i], - gamma) * e(C, - delta) = alpha_beta.
            The LHS of the equation is a triple pairing defined in bilinear_pairings/model/triple_pairing.py

        Notes:
            a_0 = 1.
        """
        out = verify_bottom_constant(self.pairing_model.modulus) if check_constant else Script()

        # stack in:  [q, ..., inverse_miller_loop_triple_pairing, A, B, C, sum_(i=0)^l a_i * gamma_abc[i]]
        # stack out: [q, ..., inverse_miller_loop_triple_pairing, A, sum_(i=0)^l a_i * gamma_abc[i], C, B,
        #               -gamma, -delta]
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
        # stack in:  [q, ..., inverse_miller_loop_triple_pairing, A, sum_(i=0)^l a_i * gamma_abc[i], C, B,
        #               -gamma, -delta]
        # stack out: [q, ..., pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta)]
        out += self.pairing_model.triple_pairing(
            modulo_threshold=modulo_threshold,
            positive_modulo=True,
            check_constant=False,
            clean_constant=clean_constant,
            is_miller_loop_proj=True,
        )

        # Verify pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta) == alpha_beta
        # stack in:  [q, ..., pairing(A,B) * pairing(sum_(i=0)^(l) a_i * gamma_abc[i], -gamma) * pairing(C, -delta)]
        # stack out: [q, ..., 0/1]
        for i, el in enumerate(locking_key.alpha_beta[::-1]):
            out += nums_to_script([el])
            out += (
                Script.parse_string("OP_EQUAL")
                if i == len(locking_key.alpha_beta) - 1
                else Script.parse_string("OP_EQUALVERIFY")
            )

        return optimise_script(out)

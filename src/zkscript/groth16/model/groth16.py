from math import log2

from tx_engine import Script

# Pairing
from src.zkscript.bilinear_pairings.model.model_definition import PairingModel

# Script implementations
# EC arithmetic
from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.elliptic_curves.ec_operations_fq_unrolled import EllipticCurveFqUnrolled
from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import nums_to_script, roll


class Groth16(PairingModel):
    def __init__(self, pairing_model, curve_a: int, r: int):
        # Pairing model used to instantiate Groth16
        self.pairing_model = pairing_model
        # A coefficient of the base curve over which Groth16 is instantiated
        self.curve_a = curve_a
        # The order of G1/G2/GT
        self.r = r

    def groth16_verifier(
        self,
        modulo_threshold: int,
        alpha_beta: list[int],
        minus_gamma: list[int],
        minus_delta: list[int],
        gamma_abc: list[list[int]],
        max_multipliers: list[int] | None = None,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Groth16 implementation.

        - gamma_abc is the list of points given in the Common Reference String.
        - max_multipliers[i] is the max value of the i-th public statement

        The verification equation is:

            e(A,B) = alpha_beta * e(sum_(i=0)^(l) a_i * gamma_abc[i], gamma) * e(C, delta)

        which we turn into:

            e(A,B) * e(sum_(i=0)^(l) a_i * gamma_abc[i], - gamma) * e(C, - delta) = alpha_beta			(*)

        These are parts of the Common Reference String obtained at setup.
        Recall that a_0 = 1.

        Input:
            Stack: q inverse_miller_loop_triple_pairing lambdas_pairing A B C
            lambda[sum_(i=0)^(l-1) a_i * gamma_abc[i], a_l * gamma_abc[l]] ..
            lambda[gamma_abc[0], a_1 * gamma_abc[1]] a_1 lambdas[a_1,gamma_abc[1]] ..
            a_l lambdas[a_l,gamma_abc[l]]
            Altstack: []
        Output:
            Verify ZKP equation

        Here:
            - a_i lambdas[a_i,gamma_abc[i]] is the input required to execute unrolled_multiplication from
            EllipticCurveFqUnrolled (except for gamma_abc[i], which is hard coded into the script)
            - lambda[sum_(i=0)^(j-1) a_i * gamma_abc[i], a_j * gamma_abc[j]] is the gradient through a_j * gamma_abc[j]
            and sum_(i=0)^(j-1) a_i * gamma_abc[i] to compute their sum
            - lambdas_pairing are the lambdas needed to execute the function self.triple_pairing() (from the Pairing
            class) to compute the triple pairing on the LHS of equation (*)
        """
        q = self.pairing_model.MODULUS
        N_POINTS_CURVE = self.pairing_model.N_POINTS_CURVE
        N_POINTS_TWIST = self.pairing_model.N_POINTS_TWIST
        n_pub = len(gamma_abc) - 1

        # Elliptic curve arithmetic
        ec_fq = EllipticCurveFq(q=q, curve_a=self.curve_a)
        # Unrolled EC arithmetic
        ec_fq_unrolled = EllipticCurveFqUnrolled(q=q, ec_over_fq=ec_fq)

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([q])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

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
            if not any(gamma_abc[i]):
                out += Script.parse_string(" ".join(["0x00"] * N_POINTS_CURVE))
            else:
                out += nums_to_script(gamma_abc[i])
            if i > 0:
                max_multiplier = self.r if max_multipliers is None else max_multipliers[i - 1]
                out += ec_fq_unrolled.unrolled_multiplication(
                    max_multiplier=max_multiplier,
                    modulo_threshold=modulo_threshold,
                    check_constant=False,
                    clean_constant=False,
                )
                out += Script.parse_string("OP_2SWAP OP_2DROP")  # Drop gamma_abc[i]
                out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * N_POINTS_CURVE))

        # After this, the stack is: q .. lambdas_pairing inverse_miller_loop_triple_pairing A B C
        # sum_(i=0)^l a_i * gamma_abc[i]
        for _i in range(n_pub):
            out += Script.parse_string(" ".join(["OP_FROMALTSTACK"] * N_POINTS_CURVE))
            out += ec_fq.point_addition_with_unknown_points(
                take_modulo=True, check_constant=False, clean_constant=False
            )

        # After this, the stack is: q .. lambdas_pairing inverse_miller_loop_triple_pairing A
        # sum_(i=0)^l a_i * gamma_abc[i] C B gamma delta
        out += roll(position=2 * N_POINTS_CURVE - 1, n_elements=N_POINTS_CURVE)  # Roll C
        out += roll(position=2 * N_POINTS_CURVE + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)  # Roll B
        out += nums_to_script(minus_gamma)
        out += nums_to_script(minus_delta)

        # After this, the stack is: q .. e(A,B) * e(sum_(i=0)^(l) a_i * gamma_abc[i], gamma) * e(C, delta)
        out += self.pairing_model.triple_pairing(
            modulo_threshold=modulo_threshold, check_constant=False, clean_constant=clean_constant
        )

        # After this, the top of the stack is:
        # [e(A,B) * e(sum_(i=0)^(l) a_i * gamma_abc[i], gamma) * e(C, delta) ?= alpha_beta]
        for ix, el in enumerate(alpha_beta[::-1]):
            out += nums_to_script([el])
            if ix != len(alpha_beta) - 1:
                out += Script.parse_string("OP_EQUALVERIFY")
            else:
                out += Script.parse_string("OP_EQUAL")

        return optimise_script(out)

    def groth16_verifier_unlock(
        self,
        pub: list[int],
        A: list[int],
        B: list[int],
        C: list[int],
        lambdas_B_exp_miller_loop: list[list[list[int]]],
        lambdas_minus_gamma_exp_miller_loop: list[list[list[int]]],
        lambdas_minus_delta_exp_miller_loop: list[list[list[int]]],
        inverse_miller_loop: list[int],
        lamdbas_partial_sums: list[int],
        lambdas_multiplications: list[int],
        max_multipliers: list[int] | None = None,
        load_q=True,
    ) -> Script:
        r"""Generate unlocking script for groth16_verifier.

        - pub: list of public statements
        - (A,B,C): zk-proof, elements passed as their list of coordinates
        - lambdas_B_exp_miller_loop: gradients needed to compute val * B, see also unrolled_multiplication in
        EllipticCurveFqUnrolled (val is the value over which we compute the Miller loop)
        - lambdas_minus_gamma_exp_miller_loop: gradients needed to compute val * (-gamma)
        - lambdas_minus_delta_exp_miller_loop: gradients needed to compute val * (-delta)
        - inverse_miller_loop: inverse of miller_loop(A,B) * miller_loop(C,-gamma) * miller_loop(sum_gamma_abc,-delta),
        where gamma_abc is taken from the vk
        - lamdbas_partial_sums: list of gradients, the element at position n_pub - i - 1 is the list of gradients to
        compute a_(i+1) * gamma_abc[i] and \sum_(j=0)^(i) a_j * gamma_abc[j], 0 <= i <= n_pub - 1
        - lambdas_multiplications: list of gradients, the element at position i is the list of gradients to compute
        pub[i] * gamma_abc[i], 0 <= i <= n_pub - 1
        - max_multipliers[i]: upper bound for public statement pub[i]
        """
        q = self.pairing_model.MODULUS
        r = self.r
        n_pub = len(pub)

        # Lambdas for the pairing
        lambdas = []
        lambdas.append(lambdas_B_exp_miller_loop)
        lambdas.append(lambdas_minus_gamma_exp_miller_loop)
        lambdas.append(lambdas_minus_delta_exp_miller_loop)

        out = nums_to_script([q]) if load_q else Script()

        # Load z inverse
        out += nums_to_script(inverse_miller_loop)

        # Load lambdas
        for i in range(len(lambdas[0]) - 1, -1, -1):
            for j in range(len(lambdas[0][i]) - 1, -1, -1):
                for k in range(3):
                    out += nums_to_script(lambdas[k][i][j])

        # Load A, B, C
        out += nums_to_script(A)
        out += nums_to_script(B)
        out += nums_to_script(C)

        # Partial sums
        for i in range(n_pub):
            out += nums_to_script(lamdbas_partial_sums[i])

        # Multiplications pub[i] * gamma_abc[i]
        for i in range(n_pub):
            M = int(log2(r)) if max_multipliers is None else int(log2(max_multipliers[i]))

            if pub[i] == 0:
                out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0", "OP_0"] * M))
            else:
                # Binary expansion of pub[i]
                exp_pub_i = [int(bin(pub[i])[j]) for j in range(2, len(bin(pub[i])))][::-1]

                N = len(exp_pub_i) - 1

                # Marker marker_a_equal_zero
                out += Script.parse_string("OP_0")

                # Load the lambdas and the markers
                for j in range(len(lambdas_multiplications[i]) - 1, -1, -1):
                    if exp_pub_i[-j - 2] == 1:
                        out += nums_to_script(lambdas_multiplications[i][j][1]) + Script.parse_string("OP_1")
                        out += nums_to_script(lambdas_multiplications[i][j][0]) + Script.parse_string("OP_1")
                    else:
                        out += (
                            Script.parse_string("OP_0 OP_0")
                            + nums_to_script(lambdas_multiplications[i][j][0])
                            + Script.parse_string("OP_1")
                        )
                out += Script.parse_string(" ".join(["OP_0 OP_0"] * (M - N)))

        return out

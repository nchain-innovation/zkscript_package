"""pairing module.

This module enables constructing Bitcoin scripts that compute bilinear pairing.
"""

from tx_engine import Script

from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import nums_to_script, pick, roll, verify_bottom_constant


class Pairing:
    """ "Pairing class."""

    def single_pairing(
        self, modulo_threshold: int, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Bilinear pairing.

        Stack input:
            - stack:    [q, ..., miller(P,Q)^-1, lambdas, P, Q], `P` is a point on E(F_q), `Q` is a point on
                E'(F_q^{k/d}), `lambdas` is the sequence of gradients to compute the miller loop, `miller(P,Q)^-1` is
                the inverse of the miller loop
            - altstack: []

        Stack output:
            - stack:    [q, ..., e(P,Q)],
            - altstack: []

        Args:
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to evaluate the bilinear pairing e(P,Q).

        Preconditions:
            - If `P` is the point at infinity, then it is encoded as 0x00 * N_POINTS_CURVE (not OP_0)
            - If `Q` is the point at infinity, then it is encoded as 0x00 * N_POINTS_TWIST (not OP_0)
        """
        q = self.MODULUS

        easy_exponentiation_with_inverse_check = self.easy_exponentiation_with_inverse_check
        hard_exponentiation = self.hard_exponentiation

        N_POINTS_CURVE = self.N_POINTS_CURVE
        N_POINTS_TWIST = self.N_POINTS_TWIST
        N_ELEMENTS_MILLER_OUTPUT = self.N_ELEMENTS_MILLER_OUTPUT

        out = verify_bottom_constant(q) if check_constant else Script()

        # Check if Q is point at infinity, in this case, return identity
        out += pick(position=N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)
        for _ in range(N_POINTS_TWIST - 1):
            out += Script.parse_string("OP_CAT")
        out += Script.parse_string("0x" + "00" * N_POINTS_TWIST + " OP_EQUAL OP_NOT")
        out += Script.parse_string("OP_IF")

        # Otherwise, check if P is point at infinity, in this case, return identity
        out += pick(position=N_POINTS_TWIST + N_POINTS_CURVE - 1, n_elements=N_POINTS_CURVE)  # Pick P
        for _ in range(N_POINTS_CURVE - 1):
            out += Script.parse_string("OP_CAT")
        out += Script.parse_string("0x" + "00" * N_POINTS_CURVE + " OP_EQUAL OP_NOT")
        out += Script.parse_string("OP_IF")

        # Execute pairing computation

        # After this, the stack is: miller(P,Q)^-1 (t-1)Q miller(P,Q)
        out += self.miller_loop(modulo_threshold=modulo_threshold, check_constant=False, clean_constant=False)

        # This is where one would perform subgroup membership checks if they were needed
        # For Groth16, they are not, so we simply drop uQ
        out += roll(position=N_ELEMENTS_MILLER_OUTPUT + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)
        out += Script.parse_string(" ".join(["OP_DROP"] * N_POINTS_TWIST))

        out += easy_exponentiation_with_inverse_check(take_modulo=True, check_constant=False, clean_constant=False)
        out += hard_exponentiation(
            take_modulo=True, modulo_threshold=modulo_threshold, check_constant=False, clean_constant=clean_constant
        )

        # Jump here if P is point at infinity
        out += Script.parse_string("OP_ELSE")
        for _ in range((N_POINTS_TWIST + N_POINTS_CURVE) // 2):
            out += Script.parse_string("OP_2DROP")
        out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * (N_ELEMENTS_MILLER_OUTPUT - 1)))
        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")
        out += Script.parse_string("OP_ENDIF")

        # Jump here if Q is point at infinity
        out += Script.parse_string("OP_ELSE")
        for _ in range((N_POINTS_TWIST + N_POINTS_CURVE) // 2):
            out += Script.parse_string("OP_2DROP")
        out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * (N_ELEMENTS_MILLER_OUTPUT - 1)))
        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")
        out += Script.parse_string("OP_ENDIF")

        return optimise_script(out)

    def triple_pairing(
        self, modulo_threshold: int, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Product of three bilinear pairings.

        Stack input:
            - stack:    [q, ..., (miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))^-1, lambdas, P1, P2, P3, Q1, Q2, Q3],
                `Pi` are points on E(F_q), `Qi` are points on E'(F_q^{k/d}), `lambdas` is the sequence of gradients to
                compute the miller loops, `(miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))^-1` is the inverse of the
                product of the miller loops computed on each Pi,Qi
            - altstack: []

        Stack output:
            - stack:    [q, ..., e(P1,Q1) * e(P2,Q2) * e(P3,Q3)]
            - altstack: []

        Args:
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to compute the product of three bilinear pairings e(P1,Q1) * e(P2,Q2) * e(P3,Q3).

        Notes:
            At the moment, this function does not handle the case where one of the Pi's or one of the Qi's is the
            point at infinity.
        """
        q = self.MODULUS

        easy_exponentiation_with_inverse_check = self.easy_exponentiation_with_inverse_check
        hard_exponentiation = self.hard_exponentiation

        out = verify_bottom_constant(q) if check_constant else Script()

        # After this, the stack is:
        # quadratic([miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)])^-1
        # quadratic([miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)])
        out += self.triple_miller_loop(modulo_threshold=modulo_threshold, check_constant=False, clean_constant=False)

        out += easy_exponentiation_with_inverse_check(take_modulo=True, check_constant=False, clean_constant=False)
        out += hard_exponentiation(
            take_modulo=True, modulo_threshold=modulo_threshold, check_constant=False, clean_constant=clean_constant
        )

        return optimise_script(out)

    def single_pairing_input(
        self,
        point_p: list[int],
        point_q: list[int],
        lambdas_q_exp_miller_loop: list[list[list[int]]],
        miller_output_inverse: list[int] | None,
        load_q: bool = True,
    ) -> Script:
        """Returns a script containing the data required to execute the `self.single_pairing` method.

        Args:
            point_p (list[int]): Elliptic curve point on E(F_q).
            point_q (list[int]): Elliptic curve point on E'(F_q^{k/d}).
            lambdas_q_exp_miller_loop (list[list[list[int]]]): The sequence of gradients to compute the miller loop.
            miller_output_inverse (list[int] | None): The inverse of the miller loop output.
            load_q (bool): If `True`, load the modulus `q` on the stack. Defaults to `True`.

        Preconditions:
            - If `point_p` or `point_q` are the points at infinity, then they should be passed as [None, None].

        Returns:
            Script pushing [miller(P,Q)^-1, lambdas, P, Q] on the stack.
        """
        q = self.MODULUS
        N_POINTS_CURVE = self.N_POINTS_CURVE
        N_POINTS_TWIST = self.N_POINTS_TWIST

        is_p_infinity = not any(point_p)
        is_q_infinity = not any(point_q)

        out = nums_to_script([q]) if load_q else Script()

        if is_p_infinity and not is_q_infinity:
            out += Script.parse_string(" ".join(["0x00"] * N_POINTS_CURVE))
            out += nums_to_script(point_q)
        elif not is_p_infinity and is_q_infinity:
            out += nums_to_script(point_p)
            out += Script.parse_string(" ".join(["0x00"] * N_POINTS_TWIST))
        elif is_p_infinity and is_q_infinity:
            out += Script.parse_string(" ".join(["0x00"] * (N_POINTS_TWIST + N_POINTS_CURVE)))
        else:
            # Load inverse of output of Miller loop
            out += nums_to_script(miller_output_inverse)

            # Load the lambdas
            for i in range(len(lambdas_q_exp_miller_loop) - 1, -1, -1):
                for j in range(len(lambdas_q_exp_miller_loop[i]) - 1, -1, -1):
                    out += nums_to_script(lambdas_q_exp_miller_loop[i][j])

            # Load P and Q
            out += nums_to_script(point_p)
            out += nums_to_script(point_q)

        return out

    def triple_pairing_input(
        self,
        point_p1: list[int],
        point_p2: list[int],
        point_p3: list[int],
        point_q1: list[int],
        point_q2: list[int],
        point_q3: list[int],
        lambdas_q1_exp_miller_loop: list[list[list[int]]],
        lambdas_q2_exp_miller_loop: list[list[list[int]]],
        lambdas_q3_exp_miller_loop: list[list[list[int]]],
        miller_output_inverse: list[int],
        load_q: bool = True,
    ) -> Script:
        """Returns a script containing the data required to execute the `self.triple_pairing` method.

        Args:
            point_p1 (list[int]): Elliptic curve point on E(F_q).
            point_p2 (list[int]): Elliptic curve point on E(F_q).
            point_p3 (list[int]): Elliptic curve point on E(F_q).
            point_q1 (list[int]): Elliptic curve point on E'(F_q^{k/d}).
            point_q2 (list[int]): Elliptic curve point on E'(F_q^{k/d}).
            point_q3 (list[int]): Elliptic curve point on E'(F_q^{k/d}).
            lambdas_q1_exp_miller_loop (list[list[list[int]]]): The sequence of gradients to compute the miller loop.
            lambdas_q2_exp_miller_loop (list[list[list[int]]]): The sequence of gradients to compute the miller loop.
            lambdas_q3_exp_miller_loop (list[list[list[int]]]): The sequence of gradients to compute the miller loop.
            miller_output_inverse (list[int] | None): The inverse of the miller loop output.
            load_q (bool): If `True`, load the modulus `q` on the stack. Defaults to `True`.

        Returns:
            Script pushing [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]^-1, lambdas, P1, P2, P3, Q1, Q2, Q3] on the
            stack.
        """
        q = self.MODULUS
        lambdas = [lambdas_q1_exp_miller_loop, lambdas_q2_exp_miller_loop, lambdas_q3_exp_miller_loop]

        out = nums_to_script([q]) if load_q else Script()

        # Load z inverse
        out += nums_to_script(miller_output_inverse)

        # Load lambdas
        for i in range(len(lambdas[0]) - 1, -1, -1):
            for j in range(len(lambdas[0][i]) - 1, -1, -1):
                for k in range(3):
                    out += nums_to_script(lambdas[k][i][j])

        out += nums_to_script(point_p1)
        out += nums_to_script(point_p2)
        out += nums_to_script(point_p3)
        out += nums_to_script(point_q1)
        out += nums_to_script(point_q2)
        out += nums_to_script(point_q3)

        return out

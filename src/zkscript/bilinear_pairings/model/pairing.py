"""Bitcoin scripts that compute bilinear pairings."""

from tx_engine import Script

from src.zkscript.script_types.stack_elements import StackFiniteFieldElement
from src.zkscript.util.utility_functions import optimise_script
from src.zkscript.util.utility_scripts import pick, roll, verify_bottom_constant


class Pairing:
    """Pairing class."""

    def single_pairing(
        self,
        modulo_threshold: int,
        verify_gradients: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
    ) -> Script:
        """Bilinear pairing.

        Stack input:
            - stack:    [q, ..., miller(P,Q)^-1, lambdas, P, Q], `P` is a point on E(F_q), `Q` is a point on
                E'(F_q^{k/d}), `lambdas` is the sequence of gradients to compute the miller loop, `miller(P,Q)^-1` is
                the inverse of the miller loop
            - altstack: []

        Stack output:
            - stack:    [q, ..., gradients if not verify_gradients, e(P,Q)],
            - altstack: []

        Args:
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            verify_gradients (bool): If `True`, the validity of the gradients used in the Miller loop is verified.
                Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.

        Returns:
            Script to evaluate the bilinear pairing e(P,Q).

        Preconditions:
            - If `P` is the point at infinity, then it is encoded as 0x00 * N_POINTS_CURVE (not OP_0)
            - If `Q` is the point at infinity, then it is encoded as 0x00 * N_POINTS_TWIST (not OP_0)
        """
        q = self.modulus

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
        out += self.miller_loop(
            modulo_threshold=modulo_threshold,
            positive_modulo=False,
            verify_gradients=verify_gradients,
            check_constant=False,
            clean_constant=False,
        )

        gradient_tracker = (0 if verify_gradients else self.extension_degree) * sum(
            [1 if i == 0 else 2 for i in self.exp_miller_loop[:-1]]
        )

        # This is where one would perform subgroup membership checks if they were needed
        # For Groth16, they are not, so we simply drop uQ
        out += roll(position=N_ELEMENTS_MILLER_OUTPUT + N_POINTS_TWIST - 1, n_elements=N_POINTS_TWIST)
        out += Script.parse_string(" ".join(["OP_DROP"] * N_POINTS_TWIST))

        out += easy_exponentiation_with_inverse_check(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            f_inverse=StackFiniteFieldElement(
                2 * self.N_ELEMENTS_MILLER_OUTPUT - 1, False, self.N_ELEMENTS_MILLER_OUTPUT
            ).shift(gradient_tracker),
            f=StackFiniteFieldElement(self.N_ELEMENTS_MILLER_OUTPUT - 1, False, self.N_ELEMENTS_MILLER_OUTPUT),
        )
        out += hard_exponentiation(
            take_modulo=True,
            modulo_threshold=modulo_threshold,
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=clean_constant,
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
        self,
        modulo_threshold: int,
        verify_gradients: tuple[bool] = (True, True, True),
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
        is_precomputed_gradients_on_stack: bool = True,
        precomputed_gradients: list[list[list[list[int]]]] | None = None,
    ) -> Script:
        """Product of three bilinear pairings.

        Stack input:
            - stack:    [q, ..., (miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))^-1, lambdas, P1, P2, P3, Q1, Q2, Q3],
                `Pi` are points on E(F_q), `Qi` are points on E'(F_q^{k/d}), `lambdas` is the sequence of gradients to
                compute the miller loops, `(miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3))^-1` is the inverse of the
                product of the miller loops computed on each Pi,Qi
            - altstack: []

        Stack output:
            - stack:    [q, ..., non_verified_gradients, e(P1,Q1) * e(P2,Q2) * e(P3,Q3)], `non_verified_gradients`
                represents all the gradients that are not verified by the script. Verified gradients are consumed.
            - altstack: []

        Args:
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            verify_gradients (tuple[bool]): Tuple of bools detailing which of the gradients used in the Miller loop
                should be mathematically verified. Defaults to `(True,True,True)`: all the gradients are verified.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            is_precomputed_gradients_on_stack (bool): If `True`, the precomputed gradients are already on the stack,
                otherwise they are injected during the triple Miller loop. Defaults to `True`.
            precomputed_gradients (list[list[list[list[int]]]]): list of gradients required to compute the triple
                miller loop. The meaning of the lists is:
                    - precomputed_gradients[0]: gradients required to compute w*(-gamma)
                    - precomputed_gradients[1]: gradients required to compute w*(-delta)

        Returns:
            Script to compute the product of three bilinear pairings e(P1,Q1) * e(P2,Q2) * e(P3,Q3).

        Notes:
            At the moment, this function does not handle the case where one of the Pi's or one of the Qi's is the
            point at infinity.
        """
        q = self.modulus

        easy_exponentiation_with_inverse_check = self.easy_exponentiation_with_inverse_check
        hard_exponentiation = self.hard_exponentiation

        out = verify_bottom_constant(q) if check_constant else Script()

        # After this, the stack is:
        # [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]^-1
        # [miller(P1,Q1) * miller(P2,Q2) * miller(P3,Q3)]
        out += self.triple_miller_loop(
            modulo_threshold=modulo_threshold,
            positive_modulo=False,
            verify_gradients=verify_gradients,
            check_constant=False,
            clean_constant=False,
            is_precomputed_gradients_on_stack=is_precomputed_gradients_on_stack,
            precomputed_gradients=precomputed_gradients,
        )
        # Update the value of the verify_gradients vector to compute the gradient tracker.
        # If is_precomputed_gradients_on_stack is False, the last two gradients are injected and consumed
        # inside the triple miller loop, and thus are not on the stack anymore. Otherwise, they may still be
        # on the stack, and we need to count them to update gradient_tracker.
        checked_gradients = [
            verify_gradients[0],
            verify_gradients[1] or not is_precomputed_gradients_on_stack,
            verify_gradients[2] or not is_precomputed_gradients_on_stack,
        ]
        gradient_tracker = sum(self.extension_degree for gradient in checked_gradients if not gradient) * sum(
            [1 if i == 0 else 2 for i in self.exp_miller_loop[:-1]]
        )

        out += easy_exponentiation_with_inverse_check(
            take_modulo=True,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            f_inverse=StackFiniteFieldElement(
                2 * self.N_ELEMENTS_MILLER_OUTPUT - 1, False, self.N_ELEMENTS_MILLER_OUTPUT
            ).shift(gradient_tracker),
            f=StackFiniteFieldElement(self.N_ELEMENTS_MILLER_OUTPUT - 1, False, self.N_ELEMENTS_MILLER_OUTPUT),
        )

        out += hard_exponentiation(
            take_modulo=True,
            modulo_threshold=modulo_threshold,
            positive_modulo=positive_modulo,
            check_constant=False,
            clean_constant=clean_constant,
        )

        return optimise_script(out)

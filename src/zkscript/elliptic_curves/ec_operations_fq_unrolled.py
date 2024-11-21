"""Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q)."""

from math import ceil, log2

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import boolean_list_to_bitmask
from src.zkscript.util.utility_scripts import nums_to_script, roll, verify_bottom_constant


class EllipticCurveFqUnrolled:
    """Construct Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q).

    Attributes:
        MODULUS: The characteristic of the field F_q.
        EC_OVER_FQ (EllipticCurveFq): Bitcoin script instance to perform arithmetic operations over the elliptic
            curve E(F_q).
    """

    def __init__(self, q: int, ec_over_fq: EllipticCurveFq):
        """Initialise the elliptic curve group E(F_q).

        Args:
            q: The characteristic of the field F_q.
            ec_over_fq (EllipticCurveFq): Bitcoin script instance to perform arithmetic operations over the elliptic
                curve E(F_q).
        """
        self.MODULUS = q
        self.EC_OVER_FQ = ec_over_fq

    def unrolled_multiplication(
        self,
        max_multiplier: int,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Unrolled double-and-add scalar multiplication loop in E(F_q).

        Stack input:
            - stack:    [q, ..., marker_a_is_zero, gradient_operations, P := (xP, yP)], `marker_a_is_zero` is `OP_1`
                if a == 0, `gradient_operations` contains the list of gradients and operational steps obtained from the
                self.unrolled_multiplication_input method, `P` is a point on E(F_q)
            - altstack: []

        Stack output:
            - stack:    [q, ..., P, aP]
            - altstack: []

        Args:
            max_multiplier (int): The maximum value of the scalar `a`.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to multiply a point on E(F_q) using double-and-add scalar multiplication.

        Notes:
            The formula for EC point addition `P + Q` where `Q != -P` and `P` and `Q` are not the point at infinity,
            where the curve is in short Weierstrass form, is:
                `x_(P+Q) = lambda^2 - x_P - x_Q`
                `y_(P+Q) = -y_P + (x_(P+Q) - x_P) * lambda`
            where lambda is the gradient of the line through P and Q. Then, we have (with q exchanged for current_size
            in future steps):

            `log_2(abs(x_(P+Q)) <= log_2(q^2 + 2q) = log_2(q) + log_2(q+2) <= 2 log_2(q+2)`
            `log_2(abs(y_(P+Q)) <= log_2(q + (q^2 + 3q) * q) = log_2(q + q^3 + 3q^2) <= log_2(q) + log_2(1 + q^2 + 3q)`

            At every step we check that the next operation doesn't make `log_2(q) + log_2(1 + q^2 + 3q) >
            modulo_threshold`.
        """
        ec_over_fq = self.EC_OVER_FQ

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack in:  [marker_a_is_zero, [lambdas,a], P]
        # stack out: [marker_a_is_zero, [lambdas,a], P, T]
        set_T = Script.parse_string("OP_2DUP")
        out += set_T

        size_q = ceil(log2(self.MODULUS))
        current_size = size_q

        # Compute aP
        # stack in:  [marker_a_is_zero,, [lambdas, a], P, T]
        # stack out: [marker_a_s_zero, P, aP]
        for i in range(int(log2(max_multiplier)) - 1, -1, -1):
            # This is an approximation, but I'm quite sure it works.
            # We always have to take into account both operations
            # because we don't know which ones are going to be executed.
            size_after_operations = 2 * 4 * current_size
            if size_after_operations > modulo_threshold or i == 0:
                take_modulo = True
                current_size = size_q
            else:
                take_modulo = False
                current_size = size_after_operations

            # Roll marker to decide whether to execute the loop and the auxiliary data
            # stack in:  [auxiliary_data, marker_doubling, P, T]
            # stack out: [auxiliary_data, P, T, marker_doubling]
            out += roll(position=4, n_elements=1)

            # stack in:  [auxiliary_data, P, T, marker_doubling]
            # stack out: [P, T] if marker_doubling = 0, else [P, 2T]
            out += Script.parse_string("OP_IF")  # Check marker for executing iteration
            out += ec_over_fq.point_algebraic_doubling(
                take_modulo=take_modulo,
                check_constant=False,
                clean_constant=False,
                verify_gradient=True,
                gradient=StackFiniteFieldElement(4, False, 1),
                P=StackEllipticCurvePoint(
                    StackFiniteFieldElement(1, False, 1),
                    StackFiniteFieldElement(0, False, 1),
                ),
                rolling_options=boolean_list_to_bitmask([True, True]),
            )  # Compute 2T

            # Roll marker for addition and auxiliary data addition
            # stack in:  [auxiliary_data_addition, marker_addition, P, 2T]
            # stack out: [auxiliary_data_addition, P, 2T, marker_addition]
            out += roll(position=4, n_elements=1)

            # Check marker for +P and compute 2T + P if marker is 1
            # stack in:  [auxiliary_data_addition, P, 2T, marker_addition]
            # stack out: [P, 2T, if marker_addition = 0, else P, (2T+P)]
            out += Script.parse_string("OP_IF")
            out += ec_over_fq.point_algebraic_addition(
                take_modulo=take_modulo,
                check_constant=False,
                clean_constant=False,
                verify_gradient=True,
                gradient=StackFiniteFieldElement(4, False, 1),
                P=StackEllipticCurvePoint(
                    StackFiniteFieldElement(3, False, 1),
                    StackFiniteFieldElement(2, False, 1),
                ),
                Q=StackEllipticCurvePoint(
                    StackFiniteFieldElement(1, False, 1),
                    StackFiniteFieldElement(0, False, 1),
                ),
                rolling_options=boolean_list_to_bitmask([True, False, True]),
            )  # Compute 2T + P
            out += Script.parse_string("OP_ENDIF OP_ENDIF")  # Conclude the conditional branches

        # Check if a == 0
        # stack in:  [marker_a_is_zero, P, aP]
        # stack out: [P, 0x00, 0x00 if a == 0, else P aP]
        out += roll(position=4, n_elements=1)
        out += Script.parse_string("OP_IF")
        out += Script.parse_string("OP_2DROP 0x00 0x00")
        out += Script.parse_string("OP_ENDIF")

        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")

        return out

    def unrolled_multiplication_input(
        self,
        P: list[int],  # noqa: N803
        a: int,
        lambdas: list[list[list[int]]],
        max_multiplier: int,
        load_modulus=True,
    ) -> Script:
        """Gradients and operational steps related to the point doubling and addition.

        This method returns a script that can be used as the gradient_operations script used by the
        `self.unrolled_multiplication` method.

        Args:
            P (list[int]): The elliptic curve point multiplied.
            a (int): The scalar `a` used to multiply `P`.
            lambdas (list[list[list[int]]]): The sequence of gradients as required to execute the double-and-add scalar
                multiplication.
            max_multiplier (int): The maximum value of `a`.
            load_modulus (bool): If `True`, load the modulus `self.MODULUS` on the stack. Defaults to True.

        Preconditions:
            The list lamdbas is computed as follows. We denote `exp_a = (a0, a1, ..., aN)` the binary expansion of `a`.
            The function `get_lambda` is assumed to return the gradient of the line through two points.
                lambdas = []
                for i in reversed(range(len(exp_a) - 1)):
                    to_add = []
                    to_add.append(T.get_lambda(T).to_list())
                    T = T + T  # For point doubling
                    if exp_a[i] == 1:
                        to_add.append(T.get_lambda(P).to_list())  # For point addition
                    lambdas.append(to_add)
            We ignore the last element of `exp_a`, therefore `len(lambdas) = len(exp_a)-1`.

        Returns:
            Script containing the gradients and operational steps to execute double-and-add scalar multiplication.

        Notes:
            The script is based on the binary expansion of `a` (denoted `exp_a`) and the list of gradients `lambdas`.
            Here's how it is built:
            - Let `exp_a = (a0, a1, ..., aN)` where `a = sum_i 2^i * ai`, and let `M = log2(max_multiplier)`.
            - Start with the point [xP yP].
            - Iterate from `M-1` to 0:
                - If `N <= i < M`: Prepend `OP_0` to the script.
                - If `0 <= i < N`:
                    - If `exp_a[i] == 0`: Prepend `OP_0 lambda_2T OP_1`.
                    - If `exp_a[i] == 1`: Prepend `lambda_(2T+P) OP_1 lambda_2T OP_1`.
            - Prepend the modulus `q`.

            Note that we ignore the last element of exp_a (the most significant bit).

            Example 1 (a = 3, max_multiplier = 8, N = 1, M = 3):
                - `exp_a = (1,1)`, `lambdas = [[[lambda_(2T+P)], [lambda_2T]]]`
                - Resulting script: [q lambda_(2T+P) OP_1 lambda_2T OP_1 OP_0 OP_0 xP yP].

            Example 2 (a = 8, max_multiplier = 8, N = 3, M = 3):
                - `exp_a = (0,0,0,1)`, `lambdas = [[[lambda_2T]], [[lambda_2T]], [[lambda_2T]]]`
                - Resulting script: [q OP_0 lambda_2T OP_1 OP_0 lambda_2T OP_1 OP_0 lambda_2T OP_1 xP yP]

            The list indicates execution steps:
                - `OP_0`: Skip loop execution.
                - `OP_1`: Perform point doubling using the provided lambda_2T. If followed by another `OP_1`, perform
                point addition using the provided lambda_(2T+P), otherwise continue.

        Example:
            >>> from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
            >>>
            >>> P = [6, 11]
            >>> ec_curve = EllipticCurveFq(q=17, curve_a=0)
            >>> ec_curve_unrolled = EllipticCurveFqUnrolled(q=17, ec_over_fq=ec_curve)
            >>> a = 3
            >>> lambdas = [[[8], [10]]]
            >>> ec_curve_unrolled.unrolled_multiplication_input(P, a, lambdas, max_multiplier=8)
            0x11 OP_0 OP_10 OP_1 OP_8 OP_1 OP_0 OP_0 OP_6 OP_11

             ^     ^          ^         ^    ^    ^    ^    ^
             q   marker     adding   double pass pass  xP   yP
        """
        M = int(log2(max_multiplier))

        out = nums_to_script([self.MODULUS]) if load_modulus else Script()

        # Add the lambdas
        if a == 0:
            out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * M))
        else:
            exp_a = [int(bin(a)[j]) for j in range(2, len(bin(a)))][::-1]

            N = len(exp_a) - 1

            # Marker marker_a_equal_zero
            out += Script.parse_string("OP_0")

            # Load the lambdas and the markers
            for j in range(len(lambdas) - 1, -1, -1):
                if exp_a[-j - 2] == 1:
                    out += nums_to_script(lambdas[j][1]) + Script.parse_string("OP_1")
                    out += nums_to_script(lambdas[j][0]) + Script.parse_string("OP_1")
                else:
                    out += Script.parse_string("OP_0")
                    out += nums_to_script(lambdas[j][0])
                    out += Script.parse_string("OP_1")
            out += Script.parse_string(" ".join(["OP_0"] * (M - N)))

        # Load P
        out += nums_to_script(P)

        return out

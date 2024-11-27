"""Unlocking keys for EllipticCurveFqUnrolled."""

from dataclasses import dataclass
from math import log2

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq_unrolled import EllipticCurveFqUnrolled
from src.zkscript.util.utility_scripts import nums_to_script


@dataclass
class EllipticCurveFqUnrolledUnlockingKey:
    """Gradients and operational steps related to the point doubling and addition.

    This method returns a script that can be used as the gradient_operations script used by the
    `self.unrolled_multiplication` method.

    Args:
        P (list[int]): The elliptic curve point multiplied.
        a (int): The scalar `a` used to multiply `P`.
        gradients (list[list[list[int]]]): The sequence of gradients as required to execute the double-and-add scalar
            multiplication.
        max_multiplier (int): The maximum value of `a`.
        load_modulus (bool): If `True`, load the modulus `self.MODULUS` on the stack. Defaults to True.

    Preconditions:
        The list `gradients` is computed as follows. We denote `exp_a = (a0, a1, ..., aN)` the binary expansion of `a`.
        The function `get_gradient` is assumed to return the gradient of the line through two points.
            lambdas = []
            for i in reversed(range(len(exp_a) - 1)):
                to_add = []
                to_add.append(T.get_gradient(T).to_list())
                T = T + T  # For point doubling
                if exp_a[i] == 1:
                    to_add.append(T.get_gradient(P).to_list())  # For point addition
                lambdas.append(to_add)
        We ignore the last element of `exp_a`, therefore `len(gradients) = len(exp_a)-1`.

    Returns:
        Script containing the gradients and operational steps to execute double-and-add scalar multiplication.

    Notes:
        The script is based on the binary expansion of `a` (denoted `exp_a`) and the list of gradients `gradients`.
        Here's how it is built:
        - Let `exp_a = (a0, a1, ..., aN)` where `a = sum_i 2^i * ai`, and let `M = log2(max_multiplier)`.
        - Start with the point [xP yP].
        - Iterate from `M-1` to 0:
            - If `N <= i < M`: Prepend `OP_0` to the script.
            - If `0 <= i < N`:
                - If `exp_a[i] == 0`: Prepend `OP_0 gradient_2T OP_1`.
                - If `exp_a[i] == 1`: Prepend `gradient_(2T+P) OP_1 gradient_2T OP_1`.
        - Prepend the modulus `q`.

        Note that we ignore the last element of exp_a (the most significant bit).

        Example 1 (a = 3, max_multiplier = 8, N = 1, M = 3):
            - `exp_a = (1,1)`, `gradients = [[[gradient_(2T+P)], [gradient_2T]]]`
            - Resulting script: [q gradient_(2T+P) OP_1 gradient_2T OP_1 OP_0 OP_0 xP yP].

        Example 2 (a = 8, max_multiplier = 8, N = 3, M = 3):
            - `exp_a = (0,0,0,1)`, `gradients = [[[gradient_2T]], [[gradient_2T]], [[gradient_2T]]]`
            - Resulting script: [q OP_0 gradient_2T OP_1 OP_0 gradient_2T OP_1 OP_0 gradient_2T OP_1 xP yP]

        The list indicates execution steps:
            - `OP_0`: Skip loop execution.
            - `OP_1`: Perform point doubling using the provided gradient_2T. If followed by another `OP_1`, perform
            point addition using the provided gradient_(2T+P), otherwise continue.

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

    P: list[int]
    a: int
    gradients: list[list[list[int]]] | None
    max_multiplier: int

    def to_unlocking_script(self, unrolled_ec_over_fq: EllipticCurveFqUnrolled, load_modulus=True) -> Script:
        """Return the unlocking script required by unrolled_multiplication script.

        Args:
            unrolled_ec_over_fq (EllipticCurveFqUnrolled): The instantiation of unrolled ec arithmetic
                over Fq used to construct the unrolled_multiplication locking script.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.

        """
        M = int(log2(self.max_multiplier))

        out = nums_to_script([unrolled_ec_over_fq.MODULUS]) if load_modulus else Script()

        # Add the gradients
        if self.a == 0:
            out += Script.parse_string("OP_1") + Script.parse_string(" ".join(["OP_0"] * M))
        else:
            exp_a = [int(bin(self.a)[j]) for j in range(2, len(bin(self.a)))][::-1]

            N = len(exp_a) - 1

            # Marker marker_a_equal_zero
            out += Script.parse_string("OP_0")

            # Load the gradients and the markers
            for j in range(len(self.gradients) - 1, -1, -1):
                if exp_a[-j - 2] == 1:
                    out += nums_to_script(self.gradients[j][1]) + Script.parse_string("OP_1")
                    out += nums_to_script(self.gradients[j][0]) + Script.parse_string("OP_1")
                else:
                    out += Script.parse_string("OP_0")
                    out += nums_to_script(self.gradients[j][0])
                    out += Script.parse_string("OP_1")
            out += Script.parse_string(" ".join(["OP_0"] * (M - N)))

        # Load P
        out += nums_to_script(self.P)

        return out

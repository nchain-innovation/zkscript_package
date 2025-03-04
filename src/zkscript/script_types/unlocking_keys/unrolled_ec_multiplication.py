"""Unlocking key for `unrolled_multiplication` in EllipticCurveFq."""

from dataclasses import dataclass
from math import log2

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.types.stack_elements import StackBaseElement
from src.zkscript.util.utility_scripts import bool_to_moving_function, move, nums_to_script


@dataclass
class EllipticCurveFqUnrolledUnlockingKey:
    """Gradients and operational steps related to the point doubling and addition.

    This method returns a script that can be used as the gradient_operations script used by the
    `self.unrolled_multiplication` method.

    Args:
        P (list[int] | None): The elliptic curve point multiplied. If `None`, it means that `P` is hard-coded in the
            locking script.
        a (int): The scalar `a` used to multiply `P`.
        gradients (list[list[list[int]]]): The sequence of gradients as required to execute the double-and-add scalar
            multiplication.
        max_multiplier (int): The maximum value of `a`.
        load_modulus (bool): If `True`, load the modulus `self.modulus` on the stack. Defaults to True.

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
        Here's how it is built (when `fixed_length_unlock = False`, otherwise, each block is padded to length 4 with
        `OP_0`):
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
        >>> from src.zkscript.types.unlocking_keys.unrolled_ec_multiplication import EllipticCurveFqUnrolledUnlockingKey
        >>>
        >>> P = [6, 11]
        >>> ec_curve = EllipticCurveFq(q=17, curve_a=0)
        >>> a = 3
        >>> gradients = [[[8], [10]]]
        >>> unlocking_key = EllipticCurveFqUnrolledUnlockingKey(P, a, gradients, 8)
        >>> unlocking_key.to_unlocking_script()
        0x11 OP_0 OP_10 OP_1 OP_8 OP_1 OP_0 OP_0 OP_6 OP_11

            ^     ^          ^         ^    ^    ^    ^    ^
            q   marker     adding   double pass pass  xP   yP
    """

    P: list[int] | None
    a: int
    gradients: list[list[list[int]]] | None
    max_multiplier: int

    def to_unlocking_script(
        self,
        ec_over_fq: EllipticCurveFq,
        fixed_length_unlock: bool = False,
        load_modulus: bool = True,
        load_P: bool = True,  # noqa: N803
    ) -> Script:
        """Return the unlocking script required by unrolled_multiplication script.

        Args:
            ec_over_fq (EllipticCurveFq): The instantiation of ec arithmetic over Fq used to
                construct the unrolled_multiplication locking script.
            fixed_length_unlock (bool): If `True`, the unlocking script is padded to so that every block of
                the unrolled iteration has length 4. Defaults to `False`.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.
            load_P (bool): Whether or not to load `P` in the unlocking script. Set to `False` if `P`
                is hard-coded in the locking script.
        """
        M = int(log2(self.max_multiplier))

        out = nums_to_script([ec_over_fq.modulus]) if load_modulus else Script()

        # Add the gradients
        if self.a == 0:
            out += Script.parse_string("OP_1") + Script.parse_string(
                " ".join(["OP_0 OP_0 OP_0 OP_0"] * M if fixed_length_unlock else ["OP_0"] * M)
            )
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
                    out += Script.parse_string("OP_0 OP_0" if fixed_length_unlock else "OP_0")
                    out += nums_to_script(self.gradients[j][0])
                    out += Script.parse_string("OP_1")
            out += Script.parse_string(
                " ".join(["OP_0 OP_0 OP_0 OP_0"] * (M - N) if fixed_length_unlock else ["OP_0"] * (M - N))
            )

        # Load P
        out += nums_to_script(self.P) if load_P else Script()

        return out

    def extract_scalar_as_unsigned(self, rolling_option: bool, base_loaded: bool = True) -> Script:
        """Return the script that extracts the scalar from the stack as an unsigned number.

        Args:
            rolling_option (bool): If `True`, the bits are rolled.
            base_loaded (bool): If `True`, the script assumes that the base was loaded on the stack by the
                unlocking script. Defaults to `True`.
        """
        M = int(log2(self.max_multiplier))
        front = StackBaseElement(M * 4 - 2 - 2 * (1 - base_loaded))
        rear = StackBaseElement(M * 4 - 2 * (1 - base_loaded))

        out = Script()

        # Extract the bits
        # stack out: [.., rear[0], front[0], .., rear[M-1], front[M-1]]
        for i in range(M):
            out += move(rear.shift(-2 * i), bool_to_moving_function(rolling_option))
            out += move(front.shift(-2 * i + 1), bool_to_moving_function(rolling_option))

        out += Script.parse_string("OP_1")
        out += Script.parse_string(
            " ".join(["OP_SWAP OP_IF OP_2 OP_MUL OP_SWAP OP_IF OP_1ADD OP_ENDIF OP_ELSE OP_NIP OP_ENDIF"] * M)
        )

        return out

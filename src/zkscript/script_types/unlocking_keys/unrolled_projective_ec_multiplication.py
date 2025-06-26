"""Unlocking key for `unrolled_multiplication` in EllipticCurveFq."""

from dataclasses import dataclass
from math import log2

from tx_engine import Script

from src.zkscript.elliptic_curves.ec_operations_fq_projective import EllipticCurveFqProjective
from src.zkscript.script_types.stack_elements import StackBaseElement
from src.zkscript.util.utility_scripts import bool_to_moving_function, move, nums_to_script


@dataclass
class EllipticCurveFqProjectiveUnrolledUnlockingKey:
    """Operational steps related to the point doubling and addition.

    This method returns a script that can be used as the script used by the
    `self.unrolled_multiplication` method.

    Args:
        P (list[int] | None): The elliptic curve point multiplied. If `None`, it means that `P` is hard-coded in the
            locking script.
        a (int): The scalar `a` used to multiply `P`.
        max_multiplier (int): The maximum value of `a`.

    Returns:
        Script containing the operational steps to execute double-and-add scalar multiplication.

    Notes:
        The script is based on the binary expansion of `a` (denoted `exp_a`).
        Here's how it is built:
        - Let `exp_a = (a0, a1, ..., aN)` where `a = sum_i 2^i * ai`, and let `M = log2(max_multiplier)`.
        - Start with the point [xP, yP, zP].
        - Iterate from `M-1` to 0:
            - If `N <= i < M`: Prepend `OP_0` to the script.
            - If `0 <= i < N`:
                - If `exp_a[i] == 0`: Prepend `OP_0 OP_1`.
                - If `exp_a[i] == 1`: Prepend `OP_1 OP_1`.
        - Prepend the modulus `q`.

        Note that we ignore the last element of exp_a (the most significant bit).

        Example 1 (a = 3, max_multiplier = 8, N = 1, M = 3):
            - `exp_a = (1,1)`
            - Resulting script: [q, OP_1, OP_1, OP_0, OP_0, xP, yP].

        Example 2 (a = 8, max_multiplier = 8, N = 3, M = 3):
            - `exp_a = (0,0,0,1)`
            - Resulting script: [q, OP_0, OP_1, OP_0, OP_1, OP_0, OP_1, xP, yP]

        The list indicates execution steps:
            - `OP_0`: Skip loop execution.
            - `OP_1`: Perform point doubling using the provided gradient_2T. If followed by another `OP_1`, perform
            point addition, otherwise continue.

    Example:
        >>> from src.zkscript.elliptic_curves.ec_operations_fq_projective import EllipticCurveFqProjective
        >>> from src.zkscript.types.unlocking_keys.unrolled_projective_ec_multiplication import *
        >>>
        >>> P = [6, 11, 1]
        >>> ec_curve = EllipticCurveFq(q=17, curve_a=0)
        >>> a = 3
        >>> unlocking_key = EllipticCurveFqUnrolledUnlockingKey(P, a, 8)
        >>> unlocking_key.to_unlocking_script()
        0x11 OP_0 OP_1 OP_1 OP_0 OP_0 OP_6 OP_11

            ^     ^          ^         ^    ^    ^    ^    ^
            q   marker     adding   double pass pass  xP   yP
    """

    P: list[int] | None
    a: int
    max_multiplier: int

    def to_unlocking_script(
        self,
        ec_over_fq: EllipticCurveFqProjective,
        fixed_length_unlock: bool = False,
        load_modulus=True,
        load_P: bool = True,  # noqa: N803
    ) -> Script:
        """Return the unlocking script required by unrolled_multiplication script.

        Args:
            ec_over_fq (EllipticCurveFq): The instantiation of ec arithmetic over Fq used to
                construct the unrolled_multiplication locking script.
            fixed_length_unlock (bool): If `True`, the unlocking script is padded to so that every block of
                the unrolled iteration has length 2. Defaults to `False`.
            load_modulus (bool): Whether or not to load the modulus on the stack. Defaults to `True`.
            load_P (bool): Whether or not to load `P` in the unlocking script. Set to `False` if `P`
                is hard-coded in the locking script.
        """
        M = int(log2(self.max_multiplier))

        out = nums_to_script([ec_over_fq.modulus]) if load_modulus else Script()

        # Add the markers
        if self.a == 0:
            out += Script.parse_string("OP_1") + Script.parse_string(
                " ".join(["OP_0 OP_0"] * M if fixed_length_unlock else ["OP_0"] * M)
            )
        else:
            exp_a = [int(bin(self.a)[j]) for j in range(2, len(bin(self.a)))]

            N = len(exp_a) - 1

            # Marker marker_a_equal_zero
            out += Script.parse_string("OP_0")

            # Load the gradients and the markers
            for e in exp_a[1:][::-1]:
                if e == 1:
                    out += Script.parse_string("OP_1 OP_1")
                else:
                    out += Script.parse_string("OP_0 OP_1")
            out += Script.parse_string(" ".join(["OP_0 OP_0"] * (M - N) if fixed_length_unlock else ["OP_0"] * (M - N)))

        # Load P
        out += nums_to_script(self.P) if load_P else Script()

        return out

    @staticmethod
    def extract_scalar_as_unsigned(max_multiplier: int, rolling_option: bool, base_loaded: bool = True) -> Script:
        """Return the script that extracts the scalar from the stack as an unsigned number.

        Args:
            max_multiplier (int): The maximum value of the scalar.
            rolling_option (bool): If `True`, the bits are rolled.
            base_loaded (bool): If `True`, the script assumes that the base was loaded on the stack by the
                unlocking script. Defaults to `True`.
        """
        M = int(log2(max_multiplier))
        M = int(log2(max_multiplier))
        element = StackBaseElement(M * 2 - 1 + 3 * base_loaded)

        out = Script()

        # Extract the bits
        # stack out: [.., rear[0], front[0], .., rear[M-1], front[M-1]]
        for _ in range(2 * M):
            out += move(element, bool_to_moving_function(rolling_option))

        out += Script.parse_string("OP_1")
        out += Script.parse_string(
            " ".join(["OP_SWAP OP_IF OP_2 OP_MUL OP_SWAP OP_IF OP_1ADD OP_ENDIF OP_ELSE OP_NIP OP_ENDIF"] * M)
        )

        return out

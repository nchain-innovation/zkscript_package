"""Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q)."""

from math import log2

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.script_types.stack_elements import (
    StackEllipticCurvePointProjective,
    StackFiniteFieldElement,
    StackNumber,
)
from src.zkscript.util.utility_functions import bitmask_to_boolean_list, boolean_list_to_bitmask, check_order
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    is_equal_to,
    is_mod_equal_to,
    mod,
    move,
    nums_to_script,
    pick,
    roll,
    verify_bottom_constant,
)


class EllipticCurveFqProjective:
    """Construct Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q).

    Arithmetic is performed in projective coordinates. Points are represented on the stack as a list of three
    numbers: P := [x, y, z], except for the point at infinity, which is encoded as [0x00, 0x00, 0x00]. Note that
    the points are 0x00, not OP_0. We choose this encoding to be consistent with the affine encoding, which is
    [0x00, 0x00]

    Attributes:
        modulus: The characteristic of the field F_q.
        curve_a: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
        curve_b: The `b` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
    """

    def __init__(self, q: int, curve_a: int, curve_b: int):
        """Initialise the elliptic curve group E(F_q).

        Args:
            q: The characteristic of the field F_q.
            curve_a: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
            curve_b: The `b` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
        """
        self.modulus = q
        self.curve_a = curve_a
        self.curve_b = curve_b

    def point_algebraic_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        P: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 1),  # noqa: B008
            StackFiniteFieldElement(4, False, 1),  # noqa: B008
            StackFiniteFieldElement(3, False, 1),  # noqa: B008
        ),
        Q: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(2, False, 1),  # noqa: B008
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_option: int = 3,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q` in projective
        coordinates. It also handles optional checks on the curve constant and whether the constant
        should be cleaned or reused.

        The formulas we use do not handle the point at infinity, so this script should only be used when we
        are sure that on the stack the points are not the point at infinity.

        Stack input:
            - stack    = [.., q, .., P, .., Q, ..]
            - altstack = []

        Stack output:
            - stack    = [.., q, .., P, .., Q, .., (P_+ Q_)]
            - altstack = []

        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulus (StackNumber): The position of `self.modulus` in the stack.
            P (StackEllipticCurvePointProjective): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePointProjective(
                    StackFiniteFieldElement(5,False,1)
                    StackFiniteFieldElement(4,False,1),
                    StackFiniteFieldElement(3,False,1)
                    )
            Q (StackEllipticCurvePointProjective): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePointProjective(
                    StackFiniteFieldElement(2,False,1)
                    StackFiniteFieldElement(1,False,1),
                    StackFiniteFieldElement(0,False,1)
                    )
            rolling_option (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 3 (all elements are rolled).


        Returns:
            A Bitcoin Script that computes P_ + Q_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `P` comes after `Q` in the stack
                - `Q` is not rolled
                - `Q` is not in the default position

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` != `Q_` and `P_ != -Q_` and `P_`, `Q_` not the point at infinity
        """
        check_order([P, Q])
        is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_option, 2)

        # Checks for unimplemented cases
        if not is_q_rolled:
            msg = "The current implementation only supports rolling Q."
            raise ValueError(msg)
        if Q.position != 2:  # noqa: PLR2004
            msg = "The current implementation only supports Q in position 2."
            raise ValueError(msg)

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:  [x1, y1, z1, .., x2, y2, z2]
        # stack out: [x1, y1, .., (x2*z1), (y2*z1), z2, (z1*z2)]
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
        out += move(P.z.shift(-2), bool_to_moving_function(is_p_rolled))  # Move z1
        out += Script.parse_string("OP_TUCK OP_MUL")
        out += Script.parse_string("OP_SWAP OP_FROMALTSTACK OP_OVER OP_MUL")
        out += Script.parse_string("OP_SWAP OP_FROMALTSTACK OP_TUCK OP_MUL")
        # stack in:  [x1, y1, .., (x2*z1), (y2*z1), z2, (z1*z2)]
        # stack out: [(x2*z1), (z1*z2), (x1*z2), (y1*z2), u := ±y2*z1 - (±y1*z2)]
        out += move(
            P.shift(1 - is_p_rolled), bool_to_moving_function(is_p_rolled), start_index=0, end_index=2
        )  # Move x1, y1
        out += roll(position=3, n_elements=1)  # Roll z2
        out += Script.parse_string("OP_TUCK OP_MUL OP_TOALTSTACK OP_MUL OP_ROT OP_FROMALTSTACK")
        out += Script.parse_string("OP_TUCK")
        out += Fq(self.modulus).algebraic_sum(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            x=StackFiniteFieldElement(1, Q.y.negate, 1),
            y=StackFiniteFieldElement(0, not P.y.negate, 1),
        )
        # stack in:  [(x2*z1), (z1*z2), (x1*z2), (y1*z2), u]
        # stack out: [(z1*z2), (y1*z2), u, (x1*z2), v := x2*z1 - x1*z2, v^3, v^3]
        out += roll(position=2, n_elements=1)  # Roll x1 * z2
        out += roll(position=4, n_elements=1)  # Roll x2 * z1
        out += pick(position=1, n_elements=1)  # Pick x1 * z2
        out += Script.parse_string("OP_SUB")
        out += Script.parse_string("OP_DUP OP_2DUP OP_MUL OP_MUL OP_DUP")  # Compute v^3
        # stack in:     [(z1*z2), (y1*z2), u, (x1*z2), v, v^3, v^3]
        # stack out:    [(y1*z2), u, (x1*z2), v, v^3, (z1*z2)]
        # altstack out: [v^3*z1*z2]
        out += roll(position=6, n_elements=1)  # Roll z1 * z2
        out += Script.parse_string("OP_TUCK OP_MUL OP_TOALTSTACK")
        # stack in:     [(y1*z2), u, (x1*z2), v, v^3, (z1*z2)]
        # altstack in:  [v^3*z1*z2]
        # stack out:    [(x1*z2), v, v^3, (y1*z2), u, (z1*z2*u^2)]
        # altstack out: [v^3*z1*z2]
        out += roll(position=5, n_elements=2)  # Roll y1 * z2, u
        out += roll(position=2, n_elements=1)  # Roll z1 * z2
        out += pick(position=1, n_elements=1)  # Pick u
        out += Script.parse_string("OP_DUP OP_MUL OP_MUL")  # Compute u^2 * z1 * z2
        # stack in:     [(x1*z2), v, v^3, (y1*z2), u, (z1*z2*u^2)]
        # altstack in:  [v^3*z1*z2]
        # stack out:    [u, (z1*z2*u^2), v, (x1*z2*v^2), v^3]
        # altstack out: [(v^3*z1*z2), (v^3*y1*z2)]
        out += roll(position=5, n_elements=2)  # Roll (x1*z2), v
        out += Script.parse_string("OP_TUCK OP_DUP OP_MUL OP_MUL")  # Compute x1 * z2 * v^2
        out += roll(position=5, n_elements=2)  # Roll v^3, (y1*z2)
        out += pick(position=1, n_elements=1)  # Pick v^3
        out += Script.parse_string("OP_MUL OP_TOALTSTACK")  # Compute v^3 * y1 * z2
        # stack in:     [u, (z1*z2*u^2), v, (x1*z2*v^2), v^3]
        # altstack in:  [(v^3*z1*z2), (v^3*y1*z2)]
        # stack out:    [u, v, (x1*z2*v^2), A := u^2*z1*z2 - v^3 - 2*v^2*x1*x2]
        # altstack out: [(v^3*z1*z2), (v^3*y1*z2)]
        out += pick(position=1, n_elements=1)  # Pick x1*z2*v^2
        out += Script.parse_string("OP_2 OP_MUL OP_ADD")
        out += roll(position=3, n_elements=1)  # Roll z1*z2*u^2
        out += Script.parse_string("OP_SUB OP_NEGATE")  # Compute A
        # stack in:     [u, v, (x1*z2*v^2), A := u^2*z1*z2 - v^3 - 2*v^2*x1*x2]
        # altstack in:  [(v^3*z1*z2), (v^3*y1*z2)]
        # stack out:    [vA]
        # altstack out: [(v^3*z1*z2), u * (v^2 * x1 * z2  - A) - v^3 * y1 * z2]
        out += Script.parse_string("OP_TUCK OP_SUB")
        out += roll(position=3, n_elements=1)  # Roll u
        out += Script.parse_string("OP_MUL OP_FROMALTSTACK")
        out += Fq(self.modulus).algebraic_sum(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            y=StackFiniteFieldElement(0, not P.y.negate, 1),
        )
        out += Script.parse_string("OP_TOALTSTACK OP_MUL")

        if take_modulo:
            out += move(modulus, bool_to_moving_function(clean_constant))
            out += mod(stack_preparation="", is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=False)
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def point_algebraic_doubling(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        P: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(2, False, 1),  # noqa: B008
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_option: bool = True,
    ) -> Script:
        """Perform algebraic doubling of points on an elliptic curve defined over Fq.

        This function computes the algebraic doubling of P for elliptic curve point `P` in projective
        coordinates. It also handles optional checks on the curve constant and whether the constant
        should be cleaned or reused.

        The formulas we use do not handle the point at infinity, so this script should only be used when we
        are sure that on the stack the point is not the point at infinity.

        Stack input:
            - stack    = [.., q, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [.., q, .., P, .., 2P_]
            - altstack = []

        P_ = -P not P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulus (StackNumber): The position of `self.modulus` in the stack.
            P (StackEllipticCurvePointProjective): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePointProjective(
                    StackFiniteFieldElement(2,False,1)
                    StackFiniteFieldElement(1,False,1),
                    StackFiniteFieldElement(0,False,1)
                    )
            rolling_option (bool): A boolean specifying if `P` should be rolled or picked.
                Defaults to 1 (rolled).


        Returns:
            A Bitcoin Script that computes 2P_ for the given elliptic curve point `P`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.

        Preconditions:
            - The input point `P` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` is not the point at infinity
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Bring P on top of the stack, so we can assume the stack is [x1, y1, z1]
        out += move(P, bool_to_moving_function(rolling_option))

        if self.curve_a != 0:
            # stack in:  [x1, y1, z1]
            # stack out: [x1, y1, (z1^2 * a), s := (y1 * z1)]
            out += pick(position=1, n_elements=2)  # Duplicate y1, z1
            out += pick(position=0, n_elements=1)  # Duplicate z1
            out += nums_to_script([self.curve_a])
            out += Script.parse_string("OP_MUL OP_MUL")
            out += roll(position=3, n_elements=2)  # Roll y1, z1
            out += Script.parse_string("OP_MUL")
            # stack in:     [x1, y1, (z1^2 * a), s]
            # stack out:    [x1, y1, (z1^2 * a), s]
            # altstack out: [8s^3]
            out += Script.parse_string("OP_DUP OP_2DUP OP_8 OP_MUL OP_MUL OP_MUL")
            out += Script.parse_string("OP_TOALTSTACK")
            # stack in:     [x1, y1, (z1^2 * a), s]
            # altstack in:  [8s^3]
            # stack out:    [x1, y1, (z1^2 * a), s, B := x1 * y1 * s]
            # altstack out: [8s^3]
            out += pick(position=3, n_elements=2)  # Duplicate x1, y1
            out += Script.parse_string("OP_MUL OP_OVER OP_MUL")
            # stack in:     [x1, y1, (z1^2 * a), s, B]
            # altstack in:  [8s^3]
            # stack out:    [y1, s, B, w := z1^2 * a + 3*x1^2]
            # altstack out: [8s^3]
            out += roll(position=2, n_elements=1)  # Roll z1^2 * a
            out += roll(position=4, n_elements=1)  # Roll x1
            out += Script.parse_string("OP_DUP OP_3 OP_MUL OP_MUL OP_ADD")
        else:
            # stack in:     [x1, y1, z1]
            # stack out:    [x1, y1, s]
            # altstack out: [8 * s^3]
            out += Script.parse_string("OP_OVER OP_MUL OP_DUP OP_2DUP OP_8 OP_MUL OP_MUL OP_MUL OP_TOALTSTACK")
            # stack in:     [x1, y1, s]
            # altstack in:  [8 * s^3]
            # stack out:    [x1, y1, s, B]
            # altstack out: [8 * s^3]
            out += pick(position=0, n_elements=1)  # Duplicate s
            out += pick(position=3, n_elements=2)  # Pick x1, y1
            out += Script.parse_string("OP_MUL OP_MUL")
            # stack in:     [x1, y1, s, B]
            # altstack in:  [8 * s^3]
            # stack out:    [y1, s, B, w]
            # altstack out: [8 * s^3]
            out += roll(position=3, n_elements=1)  # Roll x1
            out += Script.parse_string("OP_DUP OP_3 OP_MUL OP_MUL")
        # stack in:     [y1, s, B, w]
        # altstack in:  [8s^3]
        # stack out:    [y1, s, B, w, h := w^2 - 8B]
        # altstack out: [8s^3]
        out += pick(position=1, n_elements=2)  # Duplicate B, w
        out += Script.parse_string("OP_DUP OP_MUL OP_SWAP OP_8 OP_MUL OP_SUB")
        # stack in: [y1, s, B, w, h]
        # altstack in:  [8s^3]
        # stack out: [y1, s, h]
        # altstack out: [8s^3, w * (4B - h) - 8 * s^2 * y1^2]
        out += roll(position=2, n_elements=1)  # Roll B
        out += Script.parse_string("OP_4 OP_MUL OP_OVER OP_SUB OP_ROT OP_MUL")  # Compute w * (4B - h)
        out += pick(position=3, n_elements=2)  # Duplicate y1, s
        out += Script.parse_string("OP_MUL OP_DUP OP_MUL OP_8 OP_MUL OP_SUB OP_TOALTSTACK")
        # stack in:     [y1, s, h]
        # altstack in:  [8s^3, w * (4B - h) - 8 * s^2 * y1^2]
        # stack out:    [2sh]
        # altstack out: [8s^3, w * (4B - h) - 8 * s^2 * y1^2]
        out += Script.parse_string("OP_MUL OP_2 OP_MUL OP_NIP")
        if P.negate:
            out += Script.parse_string("OP_NEGATE")

        if take_modulo:
            out += move(modulus, bool_to_moving_function(clean_constant))
            out += mod(stack_preparation="", is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo)
            out += mod(
                stack_preparation=f"OP_FROMALTSTACK {'OP_NEGATE' if P.negate else ''} OP_ROT",
                is_positive=positive_modulo,
                is_constant_reused=False,
            )
        else:
            out += Script.parse_string(f"OP_FROMALTSTACK {'OP_NEGATE' if P.negate else ''} OP_ROT")

        return out

    def unrolled_multiplication(
        self,
        max_multiplier: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
        fixed_length_unlock: bool = False,
    ) -> Script:
        """Unrolled double-and-add scalar multiplication loop in E(F_q).

        Stack input:
            - stack:    [q, ..., marker_a_is_zero, P := (xP, yP, zP)], `marker_a_is_zero` is `OP_1`
                if a == 0, `P` is a point on E(F_q)
            - altstack: []

        Stack output:
            - stack:    [q, ..., P, aP]
            - altstack: []

        Args:
            max_multiplier (int): The maximum value of the scalar `a`.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            fixed_length_unlock (bool): If `True`, the unlocking script is expected to be padded to a fixed length
                (dependent on the `max_multiplier`). Defaults to `False`.

        Returns:
            Script to multiply a point on E(F_q) in projective coordinates using double-and-add scalar multiplication.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:  [marker_a_is_zero, P]
        # stack out: [marker_a_is_zero, P, P]
        out += Script.parse_string("OP_3DUP")
        # Compute aP
        # stack in:  [marker_a_is_zero, P, P]
        # stack out: [marker_a_s_zero, P, aP]
        for i in range(int(log2(max_multiplier)) - 1, -1, -1):
            # Roll marker to decide whether to execute the loop and the auxiliary data
            # stack in:  [auxiliary_data, marker_doubling, P, T]
            # stack out: [auxiliary_data, P, T, marker_doubling]

            out += roll(position=6, n_elements=1)

            # stack in:  [auxiliary_data, P, T, marker_doubling]
            # stack out: [P, T] if marker_doubling = 0, else [P, 2T]
            out += Script.parse_string("OP_IF")  # Check marker for executing iteration
            out += self.point_algebraic_doubling(
                take_modulo=True,
                check_constant=False,
                clean_constant=False,
                positive_modulo=positive_modulo and (i == 0),
                rolling_option=True,
            )  # Compute 2T

            # Roll marker for addition and auxiliary data addition
            # stack in:  [marker_addition, P, 2T]
            # stack out: [P, 2T, marker_addition]
            out += roll(position=6, n_elements=1)

            # Check marker for +P and compute 2T + P if marker is 1
            # stack in:  [P, 2T, marker_addition]
            # stack out: [P, 2T, if marker_addition = 0, else P, (2T+P)]
            out += Script.parse_string("OP_IF")
            out += self.point_algebraic_addition(
                take_modulo=True,
                check_constant=False,
                clean_constant=False,
                positive_modulo=positive_modulo and (i == 0),
                rolling_option=boolean_list_to_bitmask([False, True]),
            )  # Compute 2T + P

            if fixed_length_unlock:
                out += (
                    Script.parse_string("OP_ENDIF OP_ELSE")
                    + roll(position=6, n_elements=1)
                    + Script.parse_string("OP_DROP OP_ENDIF")
                )
            else:
                out += Script.parse_string("OP_ENDIF OP_ENDIF")  # Conclude the conditional branches

        # Check if a == 0
        # stack in:  [marker_a_is_zero, P, aP]
        # stack out: [P, 0x00, 0x00, 0x00 if a == 0, else P aP]
        out += roll(position=6, n_elements=1)
        out += Script.parse_string("OP_IF")
        out += Script.parse_string("OP_DROP OP_2DROP 0x00 0x00 0x00")
        out += Script.parse_string("OP_ENDIF")

        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")

        return out

    def to_affine(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
        z_inverse: StackFiniteFieldElement = StackFiniteFieldElement(3, False, 1),  # noqa: B008
        P: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(2, False, 1),  # noqa: B008
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_option: int = 3,
    ) -> Script:
        """Transform the elliptic curve point `P` into its affine form.

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            z_inverse (StackFiniteFieldElement): The position of the inverse of the z-coordinate of `P` in the stack.
                Defaults to `StackFiniteFieldElement(3, False, 1)`.
            P (StackEllipticCurvePointProjective): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePointProjective(
                    StackFiniteFieldElement(2,False,1)
                    StackFiniteFieldElement(1,False,1),
                    StackFiniteFieldElement(0,False,1)
                    )
            rolling_option (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 3 (all elements are rolled).
        """
        check_order([z_inverse, P])
        is_z_inverse_rolled, is_p_rolled = bitmask_to_boolean_list(rolling_option, 2)

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in: [q, .., z_inverse, .., x, y, z, ..]
        # stack out: [q, .., z_inverse, .., x, y, z, .., x * z_inverse, y * z_inverse, q]
        # altstack out: [z, z_inverse]
        out += move(P, bool_to_moving_function(is_p_rolled))
        out += Script.parse_string("OP_TOALTSTACK")
        out += move(z_inverse.shift(2 - 3 * is_p_rolled), bool_to_moving_function(is_z_inverse_rolled))
        out += Script.parse_string("OP_DUP OP_TOALTSTACK OP_TUCK OP_MUL OP_TOALTSTACK OP_MUL")

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo, is_constant_reused=True)
            out += mod(is_positive=positive_modulo, is_constant_reused=True)

        # stack in: [q, .., z_inverse, .., x, y, z, .., x * z_inverse, y * z_inverse, q]
        # altstack in: [z, z_inverse]
        # stack out: [q, .., z_inverse, .., x, y, z, .., x * z_inverse, y * z_inverse] or fail
        # altstack out: []
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        # Check that z != 0
        out += is_equal_to(
            target=0,
            is_verify=False,
            rolling_option=False,
        )
        out += Script.parse_string("OP_NOT OP_VERIFY")

        # Check that z * z_inverse = 1 mod q
        out += Script.parse_string("OP_MUL")
        out += is_mod_equal_to(
            clean_constant=True,
            modulus=StackNumber(1, False),
            target=1,
            is_verify=True,
            rolling_option=True,
        )

        return out

    def point_addition_with_unknown_points(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
    ) -> Script:
        """Sum two points which we do not know whether they are equal, different, or the inverse of one another.

        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., P, Q]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., (Q + P)]
            - altstack = []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            A Bitcoin script that compute the sum of `P` and `Q`, handling all possibilities.

        Preconditions:
            - P and Q are points on E(F_q) in projective coordinates.

        Notes:
            If P = -Q, then we return 0x00 0x00 0x00
            The order is important, as we carrying out computations in the projective space. The result is Q + P,
            not P + Q (the classes of the points are equivalent, but they are not equal on the nose).
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Check if Q is the point at infinity
        # stack in: [q, .., P, Q]
        # stack out: [q, .., P, Q] or move to OP_ELSE branch
        out += pick(position=2, n_elements=3)
        out += Script.parse_string("OP_CAT OP_CAT 0x000000 OP_EQUAL OP_NOT")
        out += Script.parse_string("OP_IF")

        # Check if P is the point at infinity
        # stack in: [q, .., P, Q]
        # stack out: [q, .., Q, P] or move to OP_ELSE branch
        out += roll(position=5, n_elements=3) + pick(position=2, n_elements=3)
        out += Script.parse_string("OP_CAT OP_CAT 0x000000 OP_EQUAL OP_NOT")
        out += Script.parse_string("OP_IF")

        # Check if P = - Q: (xP * zQ == xQ * zP) and (yP * zQ + yQ * zP == 0)
        # stack in: [q, .., Q, P]
        # stack out: [Q, .., Q, P] or move to OP_ELSE branch
        out += pick(position=2, n_elements=3)  # Duplicate P
        out += Script.parse_string("OP_TUCK")  # Duplicate zP
        out += pick(position=8, n_elements=2)  # Duplicate yQ zQ
        out += Script.parse_string(
            "OP_DUP OP_TOALTSTACK OP_TOALTSTACK OP_MUL OP_SWAP OP_FROMALTSTACK OP_MUL OP_ADD"
        )  # Compute yP * zQ + yQ * zP
        out += is_mod_equal_to(
            clean_constant=False,
            target=0,
            is_verify=False,
            rolling_option=True,
        )
        out += Script.parse_string("OP_FROMALTSTACK OP_2SWAP")
        out += pick(position=9, n_elements=1)  # Duplicate xQ
        out += Script.parse_string("OP_MUL OP_ROT OP_ROT OP_MUL OP_SUB")
        out += is_mod_equal_to(
            clean_constant=False,
            target=0,
            is_verify=False,
            rolling_option=True,
        )
        out += Script.parse_string("OP_BOOLAND OP_NOT OP_IF")

        # Compute Q + P
        # stack in: [q, .., Q, P]
        # stack out: [q, .., Q + P]
        out += self.point_algebraic_addition(
            take_modulo=take_modulo,
            check_constant=False,
            clean_constant=False,
            positive_modulo=positive_modulo,
            rolling_option=3,
        )

        # Come here if P = - Q
        # stack in: [q, .., Q, P]
        # stack out: [q, .., 0x00, 0x01, 0x00]
        out += Script.parse_string("OP_ELSE OP_2DROP OP_2DROP OP_2DROP 0x00 0x00 0x00 OP_ENDIF")

        # Come here if P is the point at infinity
        # stack in: [q, .., Q, P]
        # stack out: [q, .., Q]
        out += Script.parse_string("OP_ELSE OP_DROP OP_2DROP OP_ENDIF")

        # Come here if Q is the point at infinity
        # stack in: [q, .., P, Q]
        # stack out: [q, .., P]
        out += Script.parse_string("OP_ELSE OP_DROP OP_2DROP OP_ENDIF")

        out += roll(position=-1, n_elements=1) + Script.parse_string("OP_DROP") if clean_constant else Script()

        return out

    def multi_addition(
        self,
        n_points_on_stack: int,
        n_points_on_altstack: int,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
    ) -> Script:
        r"""Sum `n := n_points_on_stack + n_points_on_altstack` elliptic curve points P_1, .., P_n on E(F_q).

        Stack input:
            - stack:    [P_(n_points_on_stack), .., P_3, P_2, P_1]
            - altstack: [P_n, .., P_(n_points_on_stack+2), P_(n_points_on_stack+1)]

        Stack output:
            - stack:    [P_n + (.. + (P_(n_points_on_stack+1) + (P_1 + .. + P_(n_points_on_stack))))]
            - altstack: []

        Args:
            n_points_on_stack (int): The number of points on the stack to be summed.
            n_points_on_altstack (int): The number of points on the altstack to be summed.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.

        Returns:
            A Bitcoin script that computes the sum of of `n := n_points_on_stack + n_points_on_altstack`
            elliptic curve points in projective coordinates.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:      [P_(n_points_on_stack), .., P_3, P_2, P_1]
        # altstack in:   [P_n, .., P_(n_points_on_stack+2), P_(n_points_on_stack+1)]
        # stack out:     [P_1 + .. + P_(n_points_on_stack]
        # altstack out:  [P_n, .., P_(n_points_on_stack+2), P_(n_points_on_stack+1)]
        for i in range(n_points_on_stack - 1):
            out += self.point_addition_with_unknown_points(
                take_modulo=(i % 3 - 2 == 0), positive_modulo=False, check_constant=False, clean_constant=False
            )

        # Handle the case in which the were no points on the stack
        if n_points_on_stack == 0:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")
            n_points_on_altstack -= 1

        # stack in:      [P_1 + .. + P_(n_points_on_stack]
        # altstack in:   [P_n, .., P_(n_points_on_stack+2), P_(n_points_on_stack+1)]
        # stack out:     [P_n + .. + P_(n_points_on_stack+1) + (P_1 + .. + P_(n_points_on_stack))]
        # altstack out:  []
        for i in range(n_points_on_altstack):
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")
            out += self.point_addition_with_unknown_points(
                take_modulo=(i % 3 - 2 == 0), positive_modulo=False, check_constant=False, clean_constant=False
            )

        if take_modulo:
            # Check if the output is the point at infinity, in that case do nothing
            out += Script.parse_string("OP_3DUP OP_CAT OP_CAT 0x000000 OP_EQUAL OP_NOT OP_IF")
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            out += pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=False)
            out += Script.parse_string("OP_ENDIF")

        out += roll(position=-1, n_elements=1) + Script.parse_string("OP_DROP") if clean_constant else Script()

        return out

    def msm_with_fixed_bases(
        self,
        bases: list[list[int]],
        max_multipliers: list[int],
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
        extractable_scalars: int = 0,
    ) -> Script:
        r"""Multi-scalar multiplication script in E(F_q) with projective coordinates with fixed bases.

        This function returns the script that computes a multi-scalar multiplication. That is,
        it computes the operation:
            ((a_1, .., a_n), (P_1, .., P_n)) --> \sum_(i=1)^n a_i P_i
        where the a_i's are the scalars, and the P_i's are the bases. The script hard-codes the bases.

        Stack in:
            - stack:    [bits(a_n), .., bits(a_2), bits(a_1)]
            - altstack: []

        Stack output:
            - stack:    [a_1 * P_1 + (.. + (a_(n-1) * P_(n-1) + a_n * P_n))]
            - altstack: []

        Args:
            bases (list[list[int]]): The bases of the multi scalar multiplication, passed as a list of coordinates.
                `bases[i]` is `bases[i] = [x, y, z]` the list of the coordinates of P_i. If only two coordinates are
                passed for `bases[i]`, an additional `1` is padded as z value.
            max_multipliers (list[int]): `max_multipliers[i]` is the maximum value allowed for `a_i`.
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            extractable_scalars (int): The number of scalars that should be extractable in script. Defaults to 0.
                The extractable scalars are the first to be multiplied, i.e., the last to be loaded on the stack.

        Returns:
            A Bitcoin script that computes a multi scalar multiplication with fixed bases.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:     [a_n, .., a_2, a_1]
        # stack out:    []
        # altstack out: [a_1 * P_1, .., a_n * P_n]
        for i, (base, multiplier) in enumerate(zip(bases, max_multipliers)):
            assert len(base) != 0
            # Load `base` to the stack
            out += nums_to_script(base)
            # mapping point (x, y) = [x, y, 1]
            if len(base) == 2:  # noqa PLR2004
                out += Script.parse_string("OP_1")
            # Compute a_i * P_i
            out += self.unrolled_multiplication(
                max_multiplier=multiplier,
                check_constant=False,
                clean_constant=False,
                positive_modulo=False,
                fixed_length_unlock=(i < extractable_scalars),
            )

            # Put a_i * P_i on the altstack
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK")
            # Drop P_i
            out += Script.parse_string("OP_DROP OP_2DROP")

        # stack in:     []
        # altstack in:  [a_1 * P_1, .., a_(n-1) * P_(n-1), a_n * P_n]
        # stack out:    [a_1 * P_1 + .. + a_n * P_n]
        out += self.multi_addition(
            n_points_on_stack=0,
            n_points_on_altstack=len(bases),
            take_modulo=take_modulo,
            check_constant=False,
            clean_constant=clean_constant,
            positive_modulo=positive_modulo,
        )

        return out

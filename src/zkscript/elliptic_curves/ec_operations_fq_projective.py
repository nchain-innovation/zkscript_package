"""Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q)."""

from math import ceil, log2

from tx_engine import Script

from src.zkscript.fields.fq import Fq
from src.zkscript.types.stack_elements import StackEllipticCurvePointProjective, StackFiniteFieldElement, StackNumber
from src.zkscript.util.utility_functions import bitmask_to_boolean_list, boolean_list_to_bitmask, check_order
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    is_equal_to,
    mod,
    move,
    nums_to_script,
    pick,
    roll,
    verify_bottom_constant,
)


class EllipticCurveFqProjective:
    """Construct Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q).

    Arithmetic is performed in projective coordinates.

    Attributes:
        MODULUS: The characteristic of the field F_q.
        CURVE_A: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
        CURVE_B: The `b` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
    """

    def __init__(self, q: int, curve_a: int, curve_b: int):
        """Initialise the elliptic curve group E(F_q).

        Args:
            q: The characteristic of the field F_q.
            curve_a: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
            curve_b: The `b` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
        """
        self.MODULUS = q
        self.CURVE_A = curve_a
        self.CURVE_B = curve_b

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
        rolling_options: int = 3,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q` in projective
        coordinates.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

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
            modulus (StackNumber): The position of `self.MODULUS` in the stack.
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
            rolling_options (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 3 (all elements are rolled).


        Returns:
            A Bitcoin Script that computes P_ + Q_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `P` comes after `Q` in the stack
                - `stack_elements` is not None, but it does not contain all the keys `gradient`, `P`, `Q`

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` != `Q_` and `P_ != -Q_` and `P_`, `Q_` not the point at infinity
        """
        check_order([P, Q])
        is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_options, 2)

        # Checks for unimplemented cases
        if (not is_q_rolled) | (Q.position != 2):
            raise ValueError("The following options are not implemented:\n\t- Q is not rolled\n\t- Q is not on top of the stack")

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # stack in:  [x1, y1, z1, .., x2, y2, z2]
        # stack out: [x1, y1, .., (x2*z1), (y2*z1), z2, (z1*z2)]
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
        out += move(P.z.shift(-2), bool_to_moving_function(is_p_rolled)) # Move z1
        out += Script.parse_string("OP_TUCK OP_MUL")
        out += Script.parse_string("OP_SWAP OP_FROMALTSTACK OP_OVER OP_MUL")
        out += Script.parse_string("OP_SWAP OP_FROMALTSTACK OP_TUCK OP_MUL")
        # stack in:  [x1, y1, .., (x2*z1), (y2*z1), z2, (z1*z2)]
        # stack out: [(x2*z1), (z1*z2), (x1*z2), (y1*z2), u := ±y2*z1 - (±y1*z2)]
        out += move(P.shift(1-is_p_rolled), bool_to_moving_function(is_p_rolled), start_index=0, end_index=2) # Move x1, y1
        out += roll(position=3, n_elements=1) # Roll z2
        out += Script.parse_string("OP_TUCK OP_MUL OP_TOALTSTACK OP_MUL OP_ROT OP_FROMALTSTACK")
        out += Script.parse_string("OP_TUCK")
        out += Fq(self.MODULUS).algebraic_sum(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            x=StackFiniteFieldElement(1, P.y.negate, 1),
            y=StackFiniteFieldElement(0, not Q.y.negate, 1)
        )
        # stack in:  [(x2*z1), (z1*z2), (x1*z2), (y1*z2), u]
        # stack out: [(z1*z2), (y1*z2), u, (x1*z2), v := x2*z1 - x1*z2, v^3, v^3]
        out += roll(position=2, n_elements=1) # Roll x1 * z2
        out += roll(position=4, n_elements=1) # Roll x2 * z1
        out += pick(position=1, n_elements=1) # Pick x1 * z2
        out += Script.parse_string("OP_SUB")
        out += Script.parse_string("OP_DUP OP_2DUP OP_MUL OP_MUL OP_DUP") # Compute v^3
        # stack in:     [(z1*z2), (y1*z2), u, (x1*z2), v, v^3, v^3]
        # stack out:    [(y1*z2), u, (x1*z2), v, v^3, (z1*z2)]
        # altstack out: [v^3*z1*z2]
        out += roll(position=6, n_elements=1) # Roll z1 * z2
        out += Script.parse_string("OP_TUCK OP_MUL OP_TOALTSTACK")
        # stack in:     [(y1*z2), u, (x1*z2), v, v^3, (z1*z2)]
        # altstack in:  [v^3*z1*z2]
        # stack out:    [(x1*z2), v, v^3, (y1*z2), u, (z1*z2*u^2)]
        # altstack out: [v^3*z1*z2]
        out += roll(position=5, n_elements=2) # Roll y1 * z2, u
        out += roll(position=2, n_elements=1) # Roll z1 * z2
        out += pick(position=1, n_elements=1) # Pick u
        out += Script.parse_string("OP_DUP OP_MUL OP_MUL") # Compute u^2 * z1 * z2
        # stack in:     [(x1*z2), v, v^3, (y1*z2), u, (z1*z2*u^2)]
        # altstack in:  [v^3*z1*z2]
        # stack out:    [u, (z1*z2*u^2), v, (x1*z2*v^2), v^3]
        # altstack out: [(v^3*z1*z2), (v^3*y1*z2)]
        out += roll(position=5, n_elements=2) # Roll (x1*z2), v
        out += Script.parse_string("OP_TUCK OP_DUP OP_MUL OP_MUL") # Compute x1 * z2 * v^2
        out += roll(position=5, n_elements=2) # Roll v^3, (y1*z2)
        out += pick(position=1, n_elements=1) # Pick v^3
        out += Script.parse_string("OP_MUL OP_TOALTSTACK") # Compute v^3 * y1 * z2
        # stack in:     [u, (z1*z2*u^2), v, (x1*z2*v^2), v^3]
        # altstack in:  [(v^3*z1*z2), (v^3*y1*z2)]
        # stack out:    [u, v, (x1*z2*v^2), A := u^2*z1*z2 - v^3 - 2*v^2*x1*x2]
        # altstack out: [(v^3*z1*z2), (v^3*y1*z2)]
        out += pick(position=1, n_elements=1) # Pick x1*z2*v^2
        out += Script.parse_string("OP_2 OP_MUL OP_ADD")
        out += roll(position=3, n_elements=1) # Roll z1*z2*u^2
        out += Script.parse_string("OP_SUB OP_NEGATE") # Compute A
        # stack out:    [u, v, (x1*z2*v^2), A := u^2*z1*z2 - v^3 - 2*v^2*x1*x2]
        # altstack out: [(v^3*z1*z2), (v^3*y1*z2)]
        # stack out:    [vA]
        # altstack out: [(v^3*z1*z2), u * (v^2 * x1 * z2  - A) - v^3 * y1 * z2]
        out += Script.parse_string("OP_TUCK OP_SUB")
        out += roll(position=3, n_elements=1) # Roll u
        out += Script.parse_string("OP_MUL OP_FROMALTSTACK")
        out += Fq(self.MODULUS).algebraic_sum(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            y=StackFiniteFieldElement(0, not P.y.negate, 1)
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
        coordinates.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

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
            modulus (StackNumber): The position of `self.MODULUS` in the stack.
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
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Bring P on top of the stack, so we can assumed the stack is [x1, y1, z1]
        out += move(P, bool_to_moving_function(rolling_option))
    
        if self.CURVE_A:
            # stack in:  [x1, y1, z1]
            # stack out: [x1, y1, (z1^2 * a), s := (y1 * z1)]
            out += pick(position=1, n_elements=2) # Duplicate y1, z1
            out += pick(position=0, n_elements=1) # Duplicate z1
            out += nums_to_script([self.CURVE_A])
            out += Script.parse_string("OP_MUL OP_MUL")
            out += roll(position=3, n_elements=2) # Roll y1, z1
            out += Script.parse_string("OP_MUL")
            # stack in:     [x1, y1, (z1^2 * a), s]
            # stack out:    [x1, y1, (z1^2 * a), s]
            # altstack out: [8s^3]
            out += Script.parse_string("OP_DUP OP_2DUP OP_8 OP_MUL OP_MUL OP_MUL")
            out += Script.parse_string("OP_NEGATE OP_TOALTSTACK" if P.negate else "OP_TOALTSTACK")
            # stack in:     [x1, y1, (z1^2 * a), s]
            # altstack in:  [8s^3]
            # stack out:    [x1, y1, (z1^2 * a), s, B := x1 * y1 * s]
            # altstack out: [8s^3]
            out += pick(position=3, n_elements=2) # Duplicate x1, y1
            out += Script.parse_string("OP_MUL OP_OVER OP_MUL")
            # stack in:     [x1, y1, (z1^2 * a), s, B]
            # altstack in:  [8s^3]
            # stack out:    [y1, s, B, w := z1^2 * a + 3*x1^2]
            # altstack out: [8s^3]
            out += roll(position=2, n_elements=1) # Roll z1^2 * a
            out += roll(position=4, n_elements=1) # Roll x1
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
            out += pick(position=1, n_elements=1) # Duplicate s
            out += pick(position=3, n_elements=2) # Pick x1, y1
            out += Script.parse_string("OP_MUL OP_MUL")
            # stack in:     [x1, y1, s, B]
            # altstack in:  [8 * s^3]
            # stack out:    [y1, s, B, w]
            # altstack out: [8 * s^3]
            out += roll(position=3, n_elements=1) # Roll x1
            out += Script.parse_string("OP_DUP OP_3 OP_MUL OP_MUL")
        # stack in:     [y1, s, B, w]
        # altstack in:  [8s^3]
        # stack out:    [y1, s, B, w, h := w^2 - 8B]
        # altstack out: [8s^3]
        out += pick(position=1, n_elements=2) # Duplicate B, w
        out += Script.parse_string("OP_DUP OP_MUL OP_SWAP OP_8 OP_MUL OP_SUB")
        # stack in: [y1, s, B, w, h]
        # altstack in:  [8s^3]
        # stack out: [y1, s, h]
        # altstack out: [8s^3, w * (4B - h) - 8 * s^2 * y1^2]
        out += roll(position=2, n_elements=1) # Roll B
        out += Script.parse_string("OP_4 OP_MUL OP_OVER OP_SUB OP_ROT OP_MUL") # Compute w * (4B - h)
        out += pick(position=3, n_elements=2) # Duplicate y1, s
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
            out += mod(is_positive=positive_modulo, is_constant_reused=False)
        else:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out






"""Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q^2)."""

from tx_engine import Script

from src.zkscript.script_types.stack_elements import (
    StackEllipticCurvePoint,
    StackEllipticCurvePointProjective,
    StackFiniteFieldElement,
)
from src.zkscript.util.utility_functions import check_order
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    mod,
    move,
    nums_to_script,
    pick,
    roll,
    verify_bottom_constant,
)


class EllipticCurveFq2Projective:
    """Construct Bitcoin scripts that perform arithmetic operations over the projective elliptic curve E(F_q^2).

    Arithmetic is performed in projective coordinates. Points are represented on the stack as a list of three
    elements in Fq2: P := [x, y, z], with x  := (x0, x1), y := (y0, y1), z := (z0, z1).

    Attributes:
        modulus: The characteristic of the field F_q.
        curve_a: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q^2).
        curve_b: The `b` coefficient in the Short-Weierstrass equation of the curve (an element in F_q^2).
        FQ2 (Fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
    """

    def __init__(self, q: int, curve_a: list[int], curve_b: list[int], fq2):
        """Initialise the elliptic curve group E(F_q^2).

        Args:
            q: The characteristic of the field F_q.
            curve_a: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q^2).
            curve_b: The `b` coefficient in the Short-Weierstrass equation of the curve (an element in F_q^2).
            fq2 (Fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
        """
        self.modulus = q
        self.curve_a = curve_a
        self.curve_b = curve_b
        self.FQ2 = fq2


    def point_algebraic_doubling(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
        P: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_option: bool = True,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq2 in projective coordinates.

        Given P = [X, Y, Z] in E(F_q^2), the point 2P := [X', Y', Z'] is computed as follows:
            * T = 3X^2 + aZ^2
            * U = 2YZ
            * V = 2UXY
            * W = T^2 - 2V
            * X' = UW
            * Y' = T(V - W) - 2(UY)^2
            * Z' = U^3

        This function computes the algebraic doubling of P for elliptic curve point `P = [X, Y, Z]`
        in projective coordinates.

        Stack input:
            - stack    = [q, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [q, .., P, .., 2P_]
            - altstack = []

        P_ = -P if P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            P (StackEllipticCurvePointProjective): The position of the point `P` in the stack,
                its length, whether it should be negated.
                Defaults to: StackEllipticCurvePointProjective(
                    StackFiniteFieldElement(5, False, 2),
                    StackFiniteFieldElement(3, False, 2),
                    StackFiniteFieldElement(1, False, 2),
                )
            rolling_option (bool): If `True`, `P` is removed from the stack at the end of script execution.

        Returns:
            A Bitcoin Script that computes 2P_ for the given elliptic curve points `P`.


        Preconditions:
            - The input point `P` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - The point `P` is not the point at infinity.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        extension_degree = self.FQ2.extension_degree
        negation_coeff = -1 if P.y.negate else 1

        # stack out:    [q, .., X, {Y}, {Z}, .., UY]
        # altstack out: [U]

        out += move(P.y, bool_to_moving_function(rolling_option)) # Pick or roll Y
        out += move(P.z.shift(extension_degree), bool_to_moving_function(self.curve_a == [0,0] and rolling_option)) # Pick or roll Z
        out += Script.parse_string("OP_2OVER") # Duplicate Y

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=2*negation_coeff,
        )  # Compute U = 2YZ
        
        out += Script.parse_string("OP_2DUP OP_TOALTSTACK OP_TOALTSTACK") # Move U on the altstack

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff,
        )  # Compute UY

        # stack in:     [q, .., X, {Y}, {Z}, .., UY]
        # altstack in:  [U]
        # stack out:    [q, .., {X}, {Y}, {Z}, .., UY, X, T]
        # altstack out: [U]

        shift_value = extension_degree - (extension_degree if rolling_option else 0) * (2 if self.curve_a == [0,0] else 1)

        out += move(P.x.shift(shift_value), bool_to_moving_function(rolling_option)) # Pick or roll X
        out += Script.parse_string("OP_2DUP")
        out += self.FQ2.square(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar = 3,
        )  # Compute 3X^2
        if self.curve_a != [0,0]:
            out += move(P.z.shift(3*extension_degree), bool_to_moving_function(rolling_option)) # Pick or roll Z
            if self.curve_a[1] == 0:
                out += self.FQ2.square(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar = self.curve_a[0],
                )  # Compute aZ^2
            else:
                out += self.FQ2.square(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                )  # Compute Z^2
                out += nums_to_script(self.curve_a)
                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                )  # Compute aZ^2
            out += self.FQ2.add(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                )  # Compute T = aZ^2 + 3X^2


        # stack in:     [q, .., {X}, {Y}, {Z}, .., UY, X, T]
        # altstack in:  [U]
        # stack out:    [q, .., {X}, {Y}, {Z}, .., UY, V, T, W]
        # altstack out: [U]
        out += Script.parse_string("OP_2ROT OP_2ROT OP_2OVER")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar = 2,
        )  # Compute V = 2UXY
        out += Script.parse_string("OP_2ROT OP_2OVER OP_2")
        out += self.FQ2.base_field_scalar_mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            ) # Compute 2V
        out += Script.parse_string("OP_2OVER")
        out += self.FQ2.square(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute T^2

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute W = T^2 - 2V

        # stack in:     [q, .., {X}, {Y}, {Z}, .., UY, V, T, W]
        # altstack in:  [U]
        # stack out:    [q, .., {X}, {Y}, {Z}, .., X', Y', Z']
        # altstack out: [Z', X']

        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2DUP")

        out += self.FQ2.cube(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Z' = U^3

        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_2OVER")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute X' = UW
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_2ROT")

        # stack in:     [q, .., {X}, {Y}, {Z}, .., UY, T, W, V]
        # altstack in:  [Z', X']
        # stack out:    [q, .., {X}, {Y}, {Z}, .., T(V - W), (UY)^2]
        # altstack out: []

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute V - W

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute T(V - W)
        out += Script.parse_string("OP_2SWAP")

        out += self.FQ2.square(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar = 2
        )  # Compute 2(UY)^2

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, False, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, True, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Y' =  T(V - W) - 2(UY)^2

        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2SWAP OP_FROMALTSTACK OP_FROMALTSTACK OP")

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo)
            for _ in range(4):
                out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo)
            out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo, is_constant_reused=False)
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")
        return out

    def point_algebraic_mixed_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
        P: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(9, False, 2),  # noqa: B008
            StackFiniteFieldElement(7, False, 2),  # noqa: B008
        ),
        rolling_option: bool = True,
    ) -> Script:
        """Perform algebraic mixed addition of points on an elliptic curve defined over Fq2.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`,
        where `P` is in projective coordinates and `Q` is in affine coordinates.

        Given P = [X, Y, Z] in E(F_q^2), and Q = (X', Y'), the point P + Q := [X'', Y'', Z'']
        is computed as follows:
            * T = Y - Y'Z
            * U = X - X'Z
            * V = X + X'Z
            * W = T^2Z - U^2V
            * X'' = UW
            * Y'' = T(XU^2 - W) - YU^3
            * Z'' = U^3Z

        Stack input:
            - stack    = [q, .., Q, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [q, .., Q, .., P, .., Q_ + P_]
            - altstack = []

        P_ = -P if P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            P (StackEllipticCurvePointProjective): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePointProjective(
                     StackFiniteFieldElement(5, False, 2),
                    StackFiniteFieldElement(3, False, 2),
                    StackFiniteFieldElement(1, False, 2),
                ),
            Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                     StackFiniteFieldElement(11, False, 2),
                    StackFiniteFieldElement(9, False, 2),
                    StackFiniteFieldElement(7, False, 2),
                ),
            rolling_option (bool): If `True`, `P` and `Q` are removed from the stack at the end of script execution.


        Returns:
            A Bitcoin Script that computes Q_ + P_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `P` comes before `Q` in the stack

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `Q` is not the point at infinity.
            - `P` is not the point at infinity.
        """
        check_order([Q, P])
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        extension_degree = self.FQ2.extension_degree
        negation_coeff_Q = -1 if Q.y.negate else 1
        negation_coeff_P = -1 if P.y.negate else 1




        # stack in:     [q, .., X', Y', .., X, Y, Z, ..,]
        # stack out:    [q, .., X', {Y'}, .., X, {Y}, {Z}, .., Y, Z, T]
        # altstack out: [V, U]

        out += move(P.y, bool_to_moving_function(rolling_option))
        out += move(P.z.shift(extension_degree), bool_to_moving_function(rolling_option))
        out += Script.parse_string("OP_2OVER OP_2OVER")
        shift_val = 2*extension_degree if rolling_option else 4*extension_degree
        out += move(Q.y.shift(shift_val), bool_to_moving_function(rolling_option))
        out += Script.parse_string("OP_2OVER")
        shift_val = 3*extension_degree if rolling_option else 6*extension_degree 
        out += move(Q.x.shift(shift_val), bool_to_moving_function(rolling_option))
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute ZX'

        shift_val = 4*extension_degree if rolling_option else 6*extension_degree 
        out += move(P.x.shift(shift_val), bool_to_moving_function(False))
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
        )  # Compute V = ZX' + X
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute U = X - ZX'
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar = negation_coeff_Q
        )  # Compute U = ZY'_
        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, P.y.negate, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, True, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute T = Y_ - ZY'_

        # stack in:     [q, .., X', {Y'}, .., X, {Y}, {Z}, .., Y, Z, T]
        # altstack in:  [V, U]
        # stack out:    [q, .., {X'}, {Y'}, .., X, {Y}, {Z}, .., Y, Z, T, U, U^2, W]
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += self.FQ2.square(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute T^2
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute ZT^2

        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2DUP")
        out += self.FQ2.square(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute U^2
        out += Script.parse_string("OP_2ROT OP_2OVER OP_FROMALTSTACK OP_FROMALTSTACK")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute U^2V

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, False, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, True, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute W = T^2Z - U^2V

        # stack in:     [q, .., {X'}, {Y'}, .., X, {Y}, {Z}, .., Y, Z, T, U, U^2, W]
        # stack out:    [q, .., {X'}, {Y'}, .., {X}, {Y}, {Z}, .., X'', Y'', Z'']

        out += Script.parse_string("OP_2ROT OP_2OVER OP_2OVER")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute X'' = UW
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_2ROT")

        shift_val = 4*extension_degree if rolling_option else 6*extension_degree
        out += move(P.x.shift(shift_val), bool_to_moving_function(rolling_option))
        out += Script.parse_string("OP_2OVER")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute XU^2
        
        out += Script.parse_string("OP_2ROT OP_2ROT")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute U^3
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (XU^2 - W)
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (U^2X - W)T
        out += Script.parse_string("OP_2ROT OP_FROMALTSTACK OP_FROMALTSTACK OP_2DUP OP_2ROT")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar = negation_coeff_P
        )  # Compute YU^3
        out += Script.parse_string("OP_2ROT")
        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Y'' = T(XU^2 - W) - YU^3
        out += Script.parse_string("OP_2ROT OP_2ROT")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Z'' = U^3Z

        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2ROT OP_2ROT")

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo)
            for _ in range(4):
                out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo)
            out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo, is_constant_reused=False)
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

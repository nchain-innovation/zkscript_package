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
        self.curve_a_square = [
            (curve_a[0] ** 2 + fq2.non_residue * curve_a[1] ** 2) % q,
            (2 * curve_a[0] * curve_a[1]) % q,
        ]

    def _point_doubling_precompute(
        self,
        P: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
    ) -> Script:
        """Compute the constants A, B, C required to compute point algebraic doubling in projective coordinates.

        Given P = [X, Y, Z] in E(F_q^2), the point 2P := [X', Y', Z'] is computed as follows:
            * A = aX^2 + 6bXZ - a^2Z^2
            * B = 2aXZ + 3bZ^2
            * C = 3X^2 + aZ^2
            * X' = 2XY(Y^2 - B) - 2AYZ
            * Y' = AC + (Y^2 + B)(Y^2 - B)
            * z' = 8Y^3Z

        This function returns the script that computes A, B, and C. Note that the computation
        does not take into account whether P should be negated.

        Stack input:
            - stack    = [.., P, ..]
            - altstack = []

        Stack output:
            - stack    = [.., P, ..]
            - altstack = [C, B, A]

        Args:
            P (StackEllipticCurvePointProjective): The position of the point `P` in the stack,
                its length, whether it should be negated.
                Defaults to: StackEllipticCurvePointProjective(
                    StackFiniteFieldElement(5, False, 2),
                    StackFiniteFieldElement(3, False, 2),
                    StackFiniteFieldElement(1, False, 2),
                )
        """
        out = Script()
        extension_degree = self.FQ2.extension_degree
        _multiplication_cases = (
            lambda x, y: nums_to_script([y[0]])
            + self.FQ2.base_field_scalar_mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
            if x
            else nums_to_script(y)
            + self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
        )

        is_a_scalar = self.curve_a[1] == 0
        is_b_scalar = self.curve_b[1] == 0
        if self.curve_a != [0, 0]:
            # stack in:  [.., P, ..]
            # stack out: [.., P, .., XZ, X^2, Z^2]
            out += move(P.x, pick)  # Move X
            out += move(P.z.shift(extension_degree), pick)  # Move Z
            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute XZ

            out += Script.parse_string("OP_2ROT")

            out += self.FQ2.square(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute X^2

            out += Script.parse_string("OP_2ROT")

            out += self.FQ2.square(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute Z^2

            # stack in:  [.., P, .., XZ, X^2, Z^2]
            # stack out: [.., P, .., XZ, X^2, Z^2]
            # altstack out: [C]

            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += _multiplication_cases(is_a_scalar, self.curve_a)  # Compute aZ^2

            out += Script.parse_string("OP_2SWAP OP_3")

            out += self.FQ2.base_field_scalar_mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute 3X^2

            out += self.FQ2.add(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute 3X^2 + aZ^2

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack in: [.., P, .., XZ, X^2, Z^2]
            # altstack in: [C]
            # stack out: [.., P, .., X^2, Z^2, XZ]
            # altstack out: [C, B]
            out += Script.parse_string("OP_2ROT OP_2OVER OP_2OVER")

            out += _multiplication_cases(is_a_scalar, [i * 2 for i in self.curve_a])  # Compute 2aXZ
            out += Script.parse_string("OP_2SWAP")
            out += _multiplication_cases(is_b_scalar, [i * 3 for i in self.curve_b])  # Compute 3bZ^2
            out += self.FQ2.add(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute 2aXZ + 3bZ^2

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack in: [.., P, .., X^2, Z^2, XZ]
            # altstack in: [C, B]
            # stack out: [.., P, ..]
            # altstack out: [C, B, A]

            out += _multiplication_cases(is_b_scalar, [i * 6 for i in self.curve_b])  # Compute 6bXZ
            out += Script.parse_string("OP_2ROT")
            out += _multiplication_cases(is_a_scalar, self.curve_a)  # Compute aX^2
            out += Script.parse_string("OP_2ROT")
            out += _multiplication_cases(is_a_scalar, [-i for i in self.curve_a_square])  # Compute a^2Z^2
            out += self.FQ2.add_three(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        else:
            # stack in: [.., P, ..]
            # stack out: [.., P, .., Z, X, Z]
            # altstack out: [C]

            out += move(P.z, pick)  # Move Z
            out += move(P.x.shift(extension_degree), pick)  # Move X
            out += Script.parse_string("OP_2OVER OP_2OVER")

            out += self.FQ2.square(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
                scalar=3,
            )  # Compute C = 3X^2
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack in: [.., P, ..]
            # altstack out: [C]
            # stack out: [.., P, ..]
            # altstack out: [C, B, A]

            if is_b_scalar:
                out += self.FQ2.square(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=3 * self.curve_b[0],
                )  # Compute B = 3bZ^2

                out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=6 * self.curve_b[0],
                )  # Compute 6bXZ
            else:
                out += nums_to_script(self.curve_b)
                out += Script.parse_string("OP_2DUP OP_2ROT")
                out += self.FQ2.square(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=3,
                )  # Compute B = 3Z^2
                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                )  # Compute 3bZ^2
                out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=6,
                )  # Compute 6bX

                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                )  # Compute 6bXZ
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        return out

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
            * A = aX^2 + 6bXZ - a^2Z^2
            * B = 2aXZ + 3bZ^2
            * C = 3X^2 + aZ^2
            * X' = 2XY(Y^2 - B) - 2AYZ
            * Y' = AC + (Y^2 + B)(Y^2 - B)
            * Z' = 8Y^3Z

        This function computes the algebraic doubling of P for elliptic curve point `P = [x, y, z]`
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
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        extension_degree = self.FQ2.extension_degree
        negation_coeff = -1 if P.y.negate else 1
        # stack in:     [q, .., P, ..,]
        # stack out:    [q, .., P, ..]
        # altstack out: [C, B, A]

        out += self._point_doubling_precompute(P)

        # stack in:     [q, .., P, ..]
        # stack out:    [q, .., {P}, .., YZ_]
        # altstack out: [C, B, A, XY_, Y^2]
        out += move(P, bool_to_moving_function(rolling_option))
        # TODO this can likely be improved
        out += Script.parse_string("OP_2ROT OP_2ROT OP_2SWAP OP_2OVER")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff,
        )  # Compute XY_
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
        out += Script.parse_string("OP_2DUP")
        out += self.FQ2.square(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Y^2
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff,
        )  # Compute YZ_

        # stack in:     [q, .., {P}, .., YZ_]
        # altstack in:  [C, B, A, XY_, Y^2]
        # stack out:    [q, .., {P}, .., Z', YZ_, Y^2]
        # altstack out: [C, B, A, XY]

        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2OVER OP_2OVER")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=8,
        )  # Compute Z'
        out += Script.parse_string("OP_2ROT OP_2ROT")

        # stack in:      [q, .., {P}, .., Z', YZ_, Y^2]
        # altstack in:   [C, B, A, XY_]
        # stack out:     [q, .., {P}, .., Z', YZ_, XY_, A, Y^2 - B]
        # altstack out:  [Y']

        out += Script.parse_string("OP_FROMALTSTACK " * 4 + "OP_2DUP")
        out += Script.parse_string("OP_FROMALTSTACK " * 4 + "OP_2ROT")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute AC
        out += Script.parse_string("OP_2SWAP")
        out += move(StackFiniteFieldElement(5 * extension_degree - 1, False, extension_degree), roll)
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (Y^2 - B)
        out += Script.parse_string("OP_2ROT OP_2ROT")
        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (Y^2 + B)
        out += Script.parse_string("OP_2OVER")
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (Y^2 + B)(Y^2 - B)
        out += Script.parse_string("OP_2ROT")
        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Y'
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # stack in:      [q, .., {P}, .., Z', YZ, XY, A, Y^2 - B]
        # altstack in:   [Y']
        # stack out:     [q, .., {P}, .., Z', Y', X']
        # altstack out:  []
        out += Script.parse_string("OP_2ROT")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute XY(Y^2 + B)
        out += Script.parse_string("OP_2ROT OP_2ROT")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute AYZ

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, False, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, True, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=2,
        )  # Compute X'

        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2SWAP")
        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo)
            for _ in range(4):
                out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo)
            out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo, is_constant_reused=False)
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")
        return out

    def _point_addition_precompute(
        self,
        P: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        Q: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(11, False, 2),  # noqa: B008
            StackFiniteFieldElement(9, False, 2),  # noqa: B008
            StackFiniteFieldElement(7, False, 2),  # noqa: B008
        ),
    ) -> Script:
        """ "Compute the constants A, B, C for elliptic curve points algebraic addition in projective coordinates

        Given P = [X, Y, Z] in E(F_q^2), and Q = [X', Y', Z'], the point P + Q := [X'', Y'', Z'']
        is computed as follows:
            * A = aXX' + 3b(X'Z + XZ') - a^2ZZ'
            * B = a(X'Z + XZ') + 3bZZ'
            * C = 3XX' + aZZ'
            * X'' = (XY' + X'Y)(YY' - B) - A(YZ' + Y'Z)
            * Y'' = AC + (YY' + B)(YY' - B)
            * Z'' = (YZ' + Y'Z)(YY' + B) + C(XY' + X'Y)

        Stack input:
            - stack    = [.., Q, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [.., Q, .., P, ..]
            - altstack = [C, B, A]

        Args:
            P: (StackEllipticCurvePoint): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint = StackEllipticCurvePoint(
                    StackFiniteFieldElement(5, False, 2),
                    StackFiniteFieldElement(3, False, 2),
                    StackFiniteFieldElement(1, False, 2),
                ),
            Q (StackEllipticCurvePointProjective): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePointProjective(
                    StackFiniteFieldElement(11, False, 2),
                    StackFiniteFieldElement(9, False, 2),
                    StackFiniteFieldElement(7, False, 2),
                )
        """
        out = Script()
        extension_degree = self.FQ2.extension_degree
        _multiplication_cases = (
            lambda x, y: nums_to_script([y[0]])
            + self.FQ2.base_field_scalar_mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
            if x
            else nums_to_script(y)
            + self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
        )

        is_a_scalar = self.curve_a[1] == 0
        is_b_scalar = self.curve_b[1] == 0
        if self.curve_a != [0, 0]:
            # stack in:  [.., Q, .., P, ..]
            # stack out: [.., Q, .., P, .., (XZ' + X'Z), XX', ZZ']
            out += move(P.z, pick)  # Move Z
            out += move(Q.z.shift(extension_degree), pick)  # Move Z'
            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += move(Q.x.shift(4 * extension_degree), pick)  # Move X'
            out += move(P.x.shift(5 * extension_degree), pick)  # Move X
            out += Script.parse_string("OP_2OVER OP_2OVER")

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute XX'

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_2ROT")

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute XZ'

            out += Script.parse_string("OP_2ROT OP_2ROT")

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute XZ'

            out += self.FQ2.add(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute (XZ' + X'Z)

            out += Script.parse_string("OP_2ROT OP_2ROT")

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute ZZ'
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2SWAP")

            # stack in:  [.., Q, .., P, .., (XZ' + X'Z), XX', ZZ']
            # stack out: [.., Q, .., P, .., (XZ' + X'Z), XX', ZZ']
            # altstack out: [C]

            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += _multiplication_cases(is_a_scalar, self.curve_a)  # Compute aZZ'

            out += Script.parse_string("OP_2SWAP OP_3")

            out += self.FQ2.base_field_scalar_mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute 3XX'

            out += self.FQ2.add(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute 3XX' + aZZ'

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack in: [.., Q, .., P, .., (XZ' + X'Z), XX', ZZ']
            # altstack in: [C]
            # stack out: [.., Q, .., P, .., XX', ZZ', (XZ' + X'Z)]
            # altstack out: [C, B]
            out += Script.parse_string("OP_2ROT OP_2OVER OP_2OVER")

            out += _multiplication_cases(is_a_scalar, self.curve_a)  # Compute a(XZ' + X'Z)
            out += Script.parse_string("OP_2SWAP")

            out += _multiplication_cases(is_b_scalar, [i * 3 for i in self.curve_b])  # Compute 3bZZ'

            out += self.FQ2.add(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute a(XZ' + X'Z) + 3bZZ'

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack in: [.., Q, .., P, .., XX', ZZ', (XZ' + X'Z)]
            # altstack in: [C, B]
            # stack out: [.., Q, .., P, ..]
            # altstack out: [C, B, A]

            out += _multiplication_cases(is_b_scalar, [i * 3 for i in self.curve_b])  # Compute 3b(XZ' + X'Z)
            out += Script.parse_string("OP_2ROT")
            out += _multiplication_cases(is_a_scalar, self.curve_a)  # Compute aXX'
            out += Script.parse_string("OP_2ROT")
            out += _multiplication_cases(is_a_scalar, [-i for i in self.curve_a_square])  # Compute -a^2ZZ'
            out += self.FQ2.add_three(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        else:
            # stack in: [.., Q, .., P, ..]
            # stack out: [.., Q, .., P, .., Z, Z', Z, Z']
            # altstack out: [C]

            out += move(P.z, pick)  # Move Z
            out += move(Q.z.shift(extension_degree), pick)  # Move Z'
            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += move(P.x.shift(4 * extension_degree), pick)  # Move X
            out += move(Q.x.shift(5 * extension_degree), pick)  # Move X'

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
                scalar=3,
            )  # Compute C = 3XX'
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack out: [.., Q, .., P, .., Z, Z', Z, Z']
            # altstack out: [C]
            # stack out: [.., Q, .., P, ..]
            # altstack out: [C, B, A]

            if is_b_scalar:
                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=3 * self.curve_b[0],
                )  # Compute B = 3bZZ'

                out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            else:
                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=3,
                )  # Compute B = 3ZZ'

                out += nums_to_script(self.curve_b)
                out += Script.parse_string("OP_2DUP OP_2ROT")

                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                )  # Compute 3bZZ'
                out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK")

            out += move(P.x.shift(2 * extension_degree), pick)  # Move X
            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
                scalar=1,
            )  # Compute XZ'
            out += Script.parse_string("OP_2SWAP")

            out += move(Q.x.shift(2 * extension_degree), pick)  # Move X'
            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
                scalar=1,
            )  # Compute X'Z
            if is_b_scalar:
                out += self.FQ2.add(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=3 * self.curve_b[0],
                )  # Compute 3b(XZ' + X'Z)
            else:
                out += self.FQ2.add(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=3,
                )  # Compute 3(XZ' + X'Z)

                out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                )  # Compute 3b(XZ' + X'Z)

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        return out

    def point_algebraic_addition(
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
        Q: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(11, False, 2),  # noqa: B008
            StackFiniteFieldElement(9, False, 2),  # noqa: B008
            StackFiniteFieldElement(7, False, 2),  # noqa: B008
        ),
        rolling_option: bool = True,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq2.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`,
        where `P` and `Q` are in projective coordinates.

        Given P = [X, Y, Z] in E(F_q^2), and Q = [X', Y', Z'], the point P + Q := [X'', Y'', Z'']
        is computed as follows:
            * A = aXX' + 3b(X'Z + XZ') - a^2ZZ'
            * B = a(X'Z + XZ') + 3bZZ'
            * C = 3XX' + aZZ'
            * X'' = (XY' + X'Y)(YY' - B) - A(YZ' + Y'Z)
            * Y'' = AC + (YY' + B)(YY' - B)
            * Z'' = (YZ' + Y'Z)(YY' + B) + C(XY' + X'Y)

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
            Q (StackEllipticCurvePointProjective): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePointProjective(
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
        """
        check_order([Q, P])
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        extension_degree = self.FQ2.extension_degree
        negation_coeff_P = -1 if P.y.negate else 1
        negation_coeff_Q = -1 if Q.y.negate else 1

        # stack in:     [q, .., Q, .., P, ..]
        # stack out:    [q, .., Q, .., P, ..]
        # altstack out: [C, B, A]

        out += self._point_addition_precompute(P, Q)

        # stack in:     [q, .., Q, .., P, ..]
        # stack out:    [q, .., {Q}, .., {P}, .., YZ'_ + Y'Z_]
        # altstack out: [C, B, A, XY'_ + X'Y_, YY']

        out += move(P.y, bool_to_moving_function(rolling_option))
        shift_val = 0 if rolling_option else extension_degree
        out += move(Q.y.shift(shift_val), bool_to_moving_function(rolling_option))

        out += Script.parse_string("OP_2OVER OP_2OVER OP_2OVER OP_2OVER")
        shift_val += 5 * extension_degree
        out += move(P.x.shift(shift_val), bool_to_moving_function(rolling_option))

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_Q,
        )  # Compute XY'_

        out += Script.parse_string("OP_2SWAP")
        shift_val -= 2 * extension_degree if rolling_option else 0
        out += move(Q.x.shift(shift_val), bool_to_moving_function(rolling_option))

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_P,
        )  # Compute X'Y_

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute XY'_ + X'Y_

        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_P * negation_coeff_Q,
        )  # Compute YY'

        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        out += move(P.z.shift(2 * extension_degree), bool_to_moving_function(rolling_option))

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_Q,
        )  # Compute Y'Z_

        out += Script.parse_string("OP_2SWAP")

        shift_val = -extension_degree if rolling_option else 2 * extension_degree
        out += move(Q.z.shift(shift_val), bool_to_moving_function(rolling_option))

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_P,
        )  # Compute YZ'_

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute YZ'_ + Y'Z_

        # stack in:     [q, .., {Q}, .., {P}, .., YZ'_ + Y'Z_]
        # altstack in:  [C, B, A, XY'_ + X'Y_, YY']
        # stack out:    [q, .., {Q}, .., {P}, .., Y'', YZ'_ + Y'Z_, XY'_ + X'Y_]
        # altstack out: [C, A, YY' - B, YY' + B]

        out += Script.parse_string(
            "OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_2ROT OP_2DUP OP_FROMALTSTACK OP_FROMALTSTACK OP_2DUP OP_2ROT"
        )
        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (YY' + B)

        out += Script.parse_string("OP_2ROT OP_2ROT")

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, False, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, True, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (YY' - B)

        out += Script.parse_string(
            "OP_2ROT OP_FROMALTSTACK OP_FROMALTSTACK OP_2OVER OP_2OVER OP_2SWAP OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK"
        )
        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute AC

        out += Script.parse_string(
            "OP_2OVER OP_TOALTSTACK OP_TOALTSTACK OP_2ROT OP_2DUP OP_TOALTSTACK OP_TOALTSTACK OP_2ROT"
        )

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (YY' + B)(YY' - B)

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Y''

        out += Script.parse_string("OP_2ROT OP_2ROT")

        # stack in:      [q, .., {Q}, .., {P}, .., Y'', YZ'_ + Y'Z_, XY'_ + X'Y_]
        # altstack in:   [C, A, YY' - B, YY' + B]
        # stack out:     [q, .., {P}, .., Z'', Y'', X'']
        # altstack out:  []

        out += Script.parse_string("OP_2OVER OP_FROMALTSTACK OP_FROMALTSTACK")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (YZ'_ + Y'Z_)(YY' + B)

        out += Script.parse_string("OP_2ROT OP_2ROT OP_2DUP OP_FROMALTSTACK OP_FROMALTSTACK")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (XY'_ + X'Y_)(YY' - B)

        out += Script.parse_string("OP_2ROT OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_2ROT")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=-1,
        )  # Compute A(YZ_' + Y'Z_)

        out += Script.parse_string("OP_2ROT")

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute X''

        out += Script.parse_string("OP_2ROT OP_2ROT")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute C(XY' + X'Y)
        out += Script.parse_string("OP_2ROT")

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Z''

        out += Script.parse_string("OP_2ROT OP_2ROT")

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo)
            for _ in range(4):
                out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo)
            out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo, is_constant_reused=False)
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

    def _point_mixed_addition_precompute(
        self,
        P: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(9, False, 2),  # noqa: B008
            StackFiniteFieldElement(7, False, 2),  # noqa: B008
        ),
    ) -> Script:
        """ "Compute the constants A, B, C for elliptic curve mixed point addition.

        Given P = [X, Y, Z] in E(F_q^2), and Q = (X', Y'), the point P + proj(Q) := [X'', Y'', Z'']
        is computed as follows:
            * A = aXX' + 3b(X'Z + X) - a^2Z
            * B = a(X'Z + X) + 3bZ
            * C = 3XX' + aZ
            * X'' = (XY' + X'Y)(YY' - B) - A(Y + Y'Z)
            * Y'' = AC + (YY' + B)(YY' - B)
            * Z'' = (Y + Y'Z)(YY' + B) + C(XY' + X'Y)

        Stack input:
            - stack    = [.., Q, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [.., Q, .., P, ..]
            - altstack = [C, B, A]

        Args:
            P: (StackEllipticCurvePoint): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint = StackEllipticCurvePoint(
                    StackFiniteFieldElement(5, False, 2),
                    StackFiniteFieldElement(3, False, 2),
                    StackFiniteFieldElement(1, False, 2),
                ),
            Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(9, False, 2),
                    StackFiniteFieldElement(7, False, 2),
                )
        """
        # helping variables definition
        extension_degree = self.FQ2.extension_degree
        _multiplication_cases = (
            lambda x, y: nums_to_script([y[0]])
            + self.FQ2.base_field_scalar_mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
            if x
            else nums_to_script(y)
            + self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
        )

        is_a_scalar = self.curve_a[1] == 0
        is_b_scalar = self.curve_b[1] == 0

        out = Script()

        if self.curve_a != [0, 0]:
            # stack in:  [.., Q, .., P, ..]
            # stack out: [.., Q, .., P, .., (XZ' + X'Z), XX', Z]
            out += move(P.z, pick)  # Move Z
            out += Script.parse_string("OP_2DUP")
            out += move(Q.x.shift(2 * extension_degree), pick)  # Move X'
            out += move(P.x.shift(3 * extension_degree), pick)  # Move X
            out += Script.parse_string("OP_2OVER OP_2OVER")

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute XX'

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_2ROT OP_2ROT")

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute X'Z

            out += self.FQ2.add(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute (X + X'Z)

            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2ROT")

            # stack in:  [.., Q, .., P, .., (XZ' + X'Z), XX', ZZ']
            # stack out: [.., Q, .., P, .., (XZ' + X'Z), XX', ZZ']
            # altstack out: [C]

            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += _multiplication_cases(is_a_scalar, self.curve_a)  # Compute aZZ'

            out += Script.parse_string("OP_2SWAP OP_3")

            out += self.FQ2.base_field_scalar_mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute 3XX'

            out += self.FQ2.add(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute 3XX' + aZ

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack in: [.., Q, .., P, .., (X + X'Z), XX', Z]
            # altstack in: [C]
            # stack out: [.., Q, .., P, .., XX', Z, (X + X'Z)]
            # altstack out: [C, B]
            out += Script.parse_string("OP_2ROT OP_2OVER OP_2OVER")

            out += _multiplication_cases(is_a_scalar, self.curve_a)  # Compute a(X + X'Z)
            out += Script.parse_string("OP_2SWAP")

            out += _multiplication_cases(is_b_scalar, [i * 3 for i in self.curve_b])  # Compute 3bZ

            out += self.FQ2.add(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute a(X + X'Z) + 3bZ

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack in: [.., Q, .., P, .., XX', Z, (X + X'Z)]
            # altstack in: [C, B]
            # stack out: [.., Q, .., P, ..]
            # altstack out: [C, B, A]

            out += _multiplication_cases(is_b_scalar, [i * 3 for i in self.curve_b])  # Compute 3b(X + X'Z)
            out += Script.parse_string("OP_2ROT")
            out += _multiplication_cases(is_a_scalar, self.curve_a)  # Compute aXX'
            out += Script.parse_string("OP_2ROT")
            out += _multiplication_cases(is_a_scalar, [-i for i in self.curve_a_square])  # Compute -a^2Z

            out += self.FQ2.add_three(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        else:
            # stack in: [.., Q, .., P, ..]
            # stack out: [.., Q, .., P, .., Z, Z]
            # altstack out: [C]

            out += move(P.z, pick)  # Move Z
            out += Script.parse_string("OP_2DUP")
            out += move(P.x.shift(2 * extension_degree), pick)  # Move X
            out += move(Q.x.shift(3 * extension_degree), pick)  # Move X'
            out += Script.parse_string("OP_2OVER")
            out += Script.parse_string("OP_2OVER")

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
                scalar=3,
            )  # Compute C = 3XX'
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack out: [.., Q, .., P, .., Z, Z, X, X']
            # altstack out: [C]
            # stack out: [.., Q, .., P, .., Z, X, X']
            # altstack out: [C, B]
            out += Script.parse_string("OP_2ROT")
            out += _multiplication_cases(is_b_scalar, [3 * i for i in self.curve_b])  # compute 3bZ
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            # stack out: [.., Q, .., P, .., Z, X, X']
            # altstack out: [C, B]
            # stack out: [.., Q, .., P, ..]
            # altstack out: [C, B, A]

            out += Script.parse_string("OP_2ROT")

            out += self.FQ2.mul(
                take_modulo=False,
                positive_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # Compute X'Z

            if is_b_scalar:
                out += self.FQ2.add(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=3 * self.curve_b[0],
                )  # Compute 3b(X + X'Z)
            else:
                out += self.FQ2.add(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                    scalar=1,
                )  # Compute (X + X'Z)
                out += nums_to_script([3 * i for i in self.curve_b])
                out += self.FQ2.mul(
                    take_modulo=False,
                    positive_modulo=False,
                    check_constant=False,
                    clean_constant=False,
                    is_constant_reused=False,
                )  # Compute 3b(X + X'Z)

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

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
            * A = aXX' + 3b(X'Z + X) - a^2Z
            * B = a(X'Z + X) + 3bZ
            * C = 3XX' + aZ
            * X'' = (XY' + X'Y)(YY' - B) - A(Y + Y'Z)
            * Y'' = AC + (YY' + B)(YY' - B)
            * Z'' = (Y + Y'Z)(YY' + B) + C(XY' + X'Y)

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
            - Q is not the point at infinity.
        """
        check_order([Q, P])
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        extension_degree = self.FQ2.extension_degree
        negation_coeff_P = -1 if P.y.negate else 1
        negation_coeff_Q = -1 if Q.y.negate else 1

        # stack in:     [q, .., Q, .., P, ..]
        # stack out:    [q, .., Q, .., P, ..]
        # altstack out: [C, B, A]

        out += self._point_mixed_addition_precompute(P, Q)

        # stack in:     [q, .., Q, .., P, ..]
        # stack out:    [q, .., {Q}, .., {P}, .., YZ'_ + Y'Z_]
        # altstack out: [C, B, A, XY'_ + X'Y_, YY']

        out += move(P.y, bool_to_moving_function(rolling_option))
        shift_val = 0 if rolling_option else extension_degree
        out += move(Q.y.shift(shift_val), bool_to_moving_function(rolling_option))

        out += Script.parse_string("OP_2OVER OP_2OVER OP_2OVER OP_2OVER")
        shift_val += 5 * extension_degree
        out += move(P.x.shift(shift_val), bool_to_moving_function(rolling_option))

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_Q,
        )  # Compute XY'_

        out += Script.parse_string("OP_2SWAP")
        shift_val -= 2 * extension_degree if rolling_option else 0
        out += move(Q.x.shift(shift_val), bool_to_moving_function(rolling_option))

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_P,
        )  # Compute X'Y_

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute XY'_ + X'Y_

        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_P * negation_coeff_Q,
        )  # Compute YY'

        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        out += move(P.z.shift(2 * extension_degree), bool_to_moving_function(rolling_option))

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=negation_coeff_Q,
        )  # Compute Y'Z_

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, P.y.negate, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Y_ + Y'Z_

        # stack in:     [q, .., {Q}, .., {P}, .., Y_ + Y'Z_]
        # altstack in:  [C, B, A, XY'_ + X'Y_, YY']
        # stack out:    [q, .., {Q}, .., {P}, .., Y'', Y_ + Y'Z_, XY'_ + X'Y_]
        # altstack out: [C, A, YY' - B, YY' + B]

        out += Script.parse_string(
            "OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_2ROT OP_2DUP OP_FROMALTSTACK OP_FROMALTSTACK OP_2DUP OP_2ROT"
        )

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (YY' + B)

        out += Script.parse_string("OP_2ROT OP_2ROT")

        out += self.FQ2.algebraic_sum(
            x=StackFiniteFieldElement(2 * extension_degree - 1, False, extension_degree),
            y=StackFiniteFieldElement(extension_degree - 1, True, extension_degree),
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (YY' - B)

        out += Script.parse_string(
            "OP_2ROT OP_FROMALTSTACK OP_FROMALTSTACK OP_2OVER OP_2OVER OP_2SWAP OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK"
        )

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute AC

        out += Script.parse_string(
            "OP_2OVER OP_TOALTSTACK OP_TOALTSTACK OP_2ROT OP_2DUP OP_TOALTSTACK OP_TOALTSTACK OP_2ROT"
        )

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (YY' + B)(YY' - B)

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Y''

        out += Script.parse_string("OP_2ROT OP_2ROT")

        # stack in:      [q, .., {Q}, .., {P}, .., Y'', Y_ + Y'Z_, XY'_ + X'Y_]
        # altstack in:   [C, A, YY' - B, YY' + B]
        # stack out:     [q, .., {P}, .., Z'', Y'', X'']
        # altstack out:  []

        out += Script.parse_string("OP_2OVER OP_FROMALTSTACK OP_FROMALTSTACK")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (Y_ + Y'Z_)(YY' + B)

        out += Script.parse_string("OP_2ROT OP_2ROT OP_2DUP OP_FROMALTSTACK OP_FROMALTSTACK")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute (XY'_ + X'Y_)(YY' - B)

        out += Script.parse_string("OP_2ROT OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_2ROT")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
            scalar=-1,
        )  # Compute A(Y_ + Y'Z_)

        out += Script.parse_string("OP_2ROT")

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute X''

        out += Script.parse_string("OP_2ROT OP_2ROT")

        out += self.FQ2.mul(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute C(XY' + X'Y)
        out += Script.parse_string("OP_2ROT")

        out += self.FQ2.add(
            take_modulo=False,
            positive_modulo=False,
            check_constant=False,
            clean_constant=False,
            is_constant_reused=False,
        )  # Compute Z''

        out += Script.parse_string("OP_2ROT OP_2ROT")

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo)
            for _ in range(4):
                out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo)
            out += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo, is_constant_reused=False)
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK OP_FROMALTSTACK")

        return out

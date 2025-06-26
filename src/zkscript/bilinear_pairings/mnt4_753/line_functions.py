"""Bitcoin scripts that perform line evaluation for MNT4-753."""

from tx_engine import Script

from src.zkscript.bilinear_pairings.mnt4_753.fields import fq2_script
from src.zkscript.script_types.stack_elements import (
    StackEllipticCurvePoint,
    StackEllipticCurvePointProjective,
    StackFiniteFieldElement,
)
from src.zkscript.util.utility_functions import bitmask_to_boolean_list, check_order
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    mod,
    move,
    pick,
    roll,
    verify_bottom_constant,
)


class LineFunctions:
    """Line evaluation for MNT4-753."""

    def __init__(self, fq2):
        """Initialise line evaluation for MNT4-753.

        Args:
            fq2 (Fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
        """
        self.modulus = fq2.modulus
        self.fq2 = fq2

    def line_evaluation(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(7, False, 2),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 1),  # noqa: B008
            StackFiniteFieldElement(4, False, 1),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        r"""Evaluate line through T and Q at P.

        Stack input:
            - stack:    [q, ..., gradient, .., P, .., Q, ..], `P` is in `E(F_q)`, `Q` is in `E'(F_q^2)`, the quadratic
                twist, `gradient` is in F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., ev_(l_(T,Q)(P))], `ev_(l_(T,Q))(P)` is an element in F_q^4
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            gradient (StackFiniteFieldElement): The position of the gradient between T and Q on the stack. Defaults to
                `StackFiniteFieldElement(7, False, 2)`.
            P (StackEllipticCurvePoint): The position of the point `P` on the stack. Defaults to:
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(5, False, 1),
                    StackFiniteFieldElement(4, False, 1),
                )`
            Q (StackEllipticCurvePoint): The position of the point `Q` on the stack. Defaults to:
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(3, False, 2),
                    StackFiniteFieldElement(1, False, 2),
                )`
            rolling_options (int): Bitmask detailing which elements among `gradient`, `P`, and `Q` should be rolled.
                Defaults to 7 (everything is rolled).

        Preconditions:
            - `gradient` is the gradient through `T` and `Q`.
            - If `T = Q`, then the `gradient` is the gradient of the tangent at `T`.

        Returns:
            Script to evaluate a line through `T` and `Q` at `P`.

        Raises:
            ValueError: If either of the following happens:
             - `gradient` is between `P` and `Q`.
             - `Q` is before `P`.

        Notes:
            - `gradient` is NOT checked in this function, it is assumed to be the gradient.
            - `ev_(l_(T,Q)(P))` does NOT include the zero in the second component, this is to optimise the script size.
        """
        is_gradient_rolled, is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_options, 3)

        check_order([P, Q])

        if gradient.is_before(P):
            gradient.overlaps_on_the_right(P)
        else:
            check_order([Q, gradient])

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Line evaluation for MNT4 returns: (gradient, Q, P) --> (-yQ + gradient * (xQ - xP*u), yP) as a point in Fq4

        # Compute -yQ + gradient * (xQ - xP*u)
        # stack in:  [q .. gradient .. P .. Q ..]
        # stack out: [q .. gradient ..{xP} yP .. {xQ} yQ .. (xQ - xP*u)]
        first_component = move(Q.x, bool_to_moving_function(is_q_rolled))  # Move xQ
        first_component += move(P.x.shift(2 - 2 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move xP
        first_component += Script.parse_string("OP_SUB")
        # stack in:  [q .. gradient ..{xP} yP .. {xQ} yQ .. (xQ - xP*u)]
        # stack out: [q .. {gradient} .. {xP} yP .. {xQ} yQ .. gradient * (xQ - xP*u)]
        shift = 2 - 2 * is_q_rolled - 1 * is_p_rolled if gradient.is_before(P) else 2
        first_component += move(gradient.shift(shift), bool_to_moving_function(is_gradient_rolled))  # Move gradient
        first_component += self.fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        # stack in:     [q .. {gradient} .. {xP} yP .. {xQ} yQ .. gradient * (xQ - xP*u)]
        # stack out:    [q .. {gradient} .. {xP} yP .. {xQ} {yQ} .. (-yQ + lambda * (xQ - xP*u))_0]
        # altstack out: [(-yQ + lambda * (xQ - xP*u))_1]
        shift = 2 if gradient.is_before(P) else 2 - 2 * is_gradient_rolled
        first_component += move(Q.y.shift(shift), bool_to_moving_function(is_q_rolled), 1, 2)  # Move (yQ)_1
        if Q.negate:
            first_component += Script.parse_string("OP_ADD OP_TOALTSTACK")
        else:
            first_component += Script.parse_string("OP_SUB OP_TOALTSTACK")
        shift = 1 - 1 * is_q_rolled if gradient.is_before(P) else 1 - 1 * is_q_rolled - 2 * is_gradient_rolled
        first_component += move(Q.y.shift(shift), bool_to_moving_function(is_q_rolled), 0, 1)  # Move (yQ)_0
        if Q.negate:
            first_component += Script.parse_string("OP_ADD")
        else:
            first_component += Script.parse_string("OP_SUB")

        out += first_component

        if take_modulo:
            if clean_constant is None and is_constant_reused is None:
                msg = f"If take_modulo is set, both clean_constant: {clean_constant}"
                msg += f"and is_constant_reused: {is_constant_reused} must be set."
                raise ValueError(msg)

            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_mod_on_top=True, is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo)

            shift = 3 - 4 * is_q_rolled if gradient.is_before(P) else 3 - 4 * is_q_rolled - 2 * is_gradient_rolled
            out += move(P.y.shift(shift), bool_to_moving_function(is_p_rolled))  # Move yP
            out += Script.parse_string("OP_ROT")
            out += mod(stack_preparation="", is_constant_reused=is_constant_reused, is_positive=positive_modulo)
        else:
            out += Script.parse_string("OP_FROMALTSTACK")
            shift = 2 - 4 * is_q_rolled if gradient.is_before(P) else 2 - 4 * is_q_rolled - 2 * is_gradient_rolled
            out += move(P.y.shift(shift), bool_to_moving_function(is_p_rolled))  # Move yP

        return out

    def line_evaluation_proj(
        self,
        take_modulo: bool,
        positive_modulo: bool = True,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
        is_tangent: bool = True,
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(11, False, 1),  # noqa: B008
            StackFiniteFieldElement(10, False, 1),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(9, False, 2),  # noqa: B008
            StackFiniteFieldElement(7, False, 2),  # noqa: B008
        ),
        T: StackEllipticCurvePointProjective = StackEllipticCurvePointProjective(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        r"""Evaluate line through T and Q at P.

        For:
            P = (xP, yP) in E(Fq)
            Q = (xQ, yQ) in E(Fq2) if is_tangent is False
            T = [xT, yT, zT] in E(Fq2) in projective coordinates

        The function computes the element of Fq12 ev_(l_(T,Q)(P)) as described below:
            l1 = 3xT^2 + twisted_a * zT^2 if is_tangent else yT - yQ * zT
            l2 = 2*yT*zT if is_tangent else xT - yQ * xT
            m = conj(zT^2 * yT) if is_tangent else l1 * conj(l2)
            n = zT * l2 * conj(zT^2 * yT) if is_tangent else l2 * conj(l2)
            A = (-2 * yT^2 * zT + l1 * (xT - xP * zT * u)) * m if is_tangent else - yQ * n + m * (xQ - xP * u)
            B = yP * n
            ev_(l_(T,Q)(P)) = (A + B * r * u)/n

        We represent ev_(l_(T,Q)(P)) using 4 coordinates in Fq:

        ev_(l_(T,Q)(P)) = (A0, A1, B, n)

        Stack input:
            - stack:    [q, ..., P, .., {Q}, .., T, ..],
            - altstack: []

        Stack output:
            - stack:    [q, ..., ev_(l_(T,Q)(P))],
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, `q` remains as the second-to-top element on the stack
                after execution. Defaults to `None`.
            gradient (StackFiniteFieldElement): The position of the gradient between T and Q on the stack. Defaults to
                `StackFiniteFieldElement(7, False, 2)`.
            is_tangent (bool): Flag to decide if the line is the tangent line at T or the line trough T and Q. Default
                to `True` (the line is the tangent line at T).
            P (StackEllipticCurvePoint): The position of the point `P` on the stack. Defaults to:
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(11, False, 1),
                    StackFiniteFieldElement(10, False, 1),
                )`
            Q (StackEllipticCurvePoint): The position of the point `Q` on the stack. Defaults to:
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(9, False, 2),
                    StackFiniteFieldElement(7, False, 2),
                )`
            T (StackEllipticCurvePointProjective): The position of the point `T` on the stack. Defaults to:
                `StackEllipticCurvePointProjective(
                    StackFiniteFieldElement(5, False, 2),
                    StackFiniteFieldElement(3, False, 2),
                    StackFiniteFieldElement(1, False, 2),
                )`
            rolling_options (int): Bitmask detailing which elements among `P`, `Q`, and `T` should be rolled.
                Defaults to 7 (everything is rolled).

        Returns:
            Script to evaluate a line through `T` and `Q` at `P`.

        Raises:
            ValueError: If the order in the stack is different from P, .., Q, .., T.
        """
        is_p_rolled, is_q_rolled, is_t_rolled = bitmask_to_boolean_list(rolling_options, 3)

        check_order([P, Q, T])

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        extension_degree = 2
        if is_tangent:
            # stack in:     [q .. P .. T ..]
            # stack out:    [q .. P .. {xT} yT zT .. xT zT l1]
            out += move(T.x, moving_function=bool_to_moving_function(is_t_rolled))
            out += Script.parse_string("OP_2DUP")
            out += self.fq2.square(
                take_modulo=False, check_constant=False, clean_constant=False, scalar=3
            )  # compute 3 * xT^2
            out += move(T.z.shift(2 * extension_degree), moving_function=bool_to_moving_function(is_t_rolled))
            out += Script.parse_string("OP_2DUP")
            out += self.fq2.square(
                take_modulo=False, check_constant=False, clean_constant=False, scalar=26
            )  # compute a * zT^2
            out += Script.parse_string("OP_2ROT")

            out += self.fq2.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )  # compute l1 = 3 * xT^2 + a * zT^2

            # stack in:     [q .. P .. {xT} yT {zT} .. xT zT l1]
            # stack out:    [q .. {Px} Py .. {xT} {yT} {zT} .. m A]

            out += Script.parse_string("OP_2ROT OP_2ROT OP_2DUP")
            shift_val = 4 * extension_degree - (2 * extension_degree if is_t_rolled else 0)
            out += move(P.x.shift(shift_val), moving_function=bool_to_moving_function(is_p_rolled))
            out += self.fq2.base_field_scalar_mul(
                take_modulo=False,
                check_constant=False,
                clean_constant=False,
            )  # compute xP * zT
            out += Script.parse_string("OP_13 OP_MUL OP_SWAP")  # compute xP * zT * u
            out += Script.parse_string("OP_2ROT")
            out += self.fq2.algebraic_sum(
                x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
                y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
                take_modulo=False,
                check_constant=False,
                clean_constant=False,
            )  # compute xT - xP * u * zT

            out += Script.parse_string("OP_2ROT")
            out += self.fq2.mul(
                take_modulo=False, check_constant=False, clean_constant=False
            )  # compute l1 * (xT - xP * u * zT)
            shift_val = 2 * extension_degree - (extension_degree if is_t_rolled else 0)
            out += move(T.y.shift(shift_val), moving_function=bool_to_moving_function(is_t_rolled))

            out += Script.parse_string("OP_2ROT OP_2OVER OP_2OVER")
            out += self.fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)  # compute zT * yT
            out += Script.parse_string("OP_2DUP OP_2ROT")
            out += self.fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)  # compute zT^2 * yT
            out += Script.parse_string("OP_NEGATE")  # compute m = conj(zT^2 * yT)
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

            out += self.fq2.mul(
                take_modulo=False, check_constant=False, clean_constant=False, scalar=-2
            )  # compute -2 * yT^2 * zT
            out += self.fq2.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )  # compute -2 * yT^2* zT  + l1 * (xT - xP * u * zT )
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK OP_2DUP OP_2ROT")

            out += self.fq2.mul(
                take_modulo=take_modulo,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute  A = m * (-2 * yT^2* zT  + l1 * (xT - xP * u * zT ))

            # stack in:     [q .. {Px} Py .. {xT} {yT} {zT} .. m A]
            # stack out:    [q .. {Px} Py .. {xT} {yT} {zT} .. A B n]

            out += Script.parse_string("OP_2SWAP")

            out += self.fq2.norm(
                take_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
                scalar=2,
            )  # compute n = l2 * conj(l2/2) or l2*conj(l2)

            shift_val = extension_degree + 1 - (3 * extension_degree if is_t_rolled else 0)
            out += move(P.y.shift(shift_val), moving_function=bool_to_moving_function(is_p_rolled))
            out += Script.parse_string("OP_OVER OP_MUL")  # compute yP * n
            if take_modulo:
                out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
                out += mod(stack_preparation="", is_mod_on_top=True, is_positive=positive_modulo)
                out += mod(
                    stack_preparation="OP_ROT OP_ROT",
                    is_mod_on_top=True,
                    is_positive=positive_modulo,
                    is_constant_reused=is_constant_reused,
                )
            else:
                out += Script.parse_string("OP_SWAP")
        else:
            # stack in:     [q .. P .. Q .. T ..]
            # stack out:    [q .. P .. {Q} .. {T} .. xQ yQ l2 l1]
            out += move(Q, moving_function=bool_to_moving_function(is_q_rolled))
            out += Script.parse_string("OP_2OVER OP_2OVER")
            out += move(T.z.shift(4 * extension_degree), moving_function=bool_to_moving_function(is_t_rolled))
            out += Script.parse_string("OP_2DUP OP_2ROT")
            out += self.fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)  # compute zT * yQ
            shift_val = 4 * extension_degree if is_t_rolled else 5 * extension_degree
            out += move(T.y.shift(shift_val), moving_function=bool_to_moving_function(is_t_rolled))
            out += self.fq2.algebraic_sum(
                x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
                y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
                take_modulo=False,
                check_constant=False,
                clean_constant=False,
            )  # compute l1 = yT - zT * yQ

            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            out += self.fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)  # compute zT * xQ
            shift_val = extension_degree if is_t_rolled else 3 * extension_degree
            out += move(T.x.shift(shift_val), moving_function=bool_to_moving_function(is_t_rolled))
            out += self.fq2.algebraic_sum(
                x=StackFiniteFieldElement(2 * extension_degree - 1, True, extension_degree),
                y=StackFiniteFieldElement(extension_degree - 1, False, extension_degree),
                take_modulo=False,
                check_constant=False,
                clean_constant=False,
            )  # compute l2 = xT - zT * xQ
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

            # stack in:     [q .. P .. {Q} .. {T} .. xQ yQ l2 l1]
            # stack out:     [q .. {P} .. {Q} .. {T} .. A, B, n]

            out += Script.parse_string("OP_2OVER OP_NEGATE")  # compute conj(l2) or conj(l2/2)
            out += self.fq2.mul(
                take_modulo=False, check_constant=False, clean_constant=False
            )  # compute m = l1 * conj(l2)
            out += Script.parse_string("OP_2SWAP")
            out += self.fq2.norm(
                take_modulo=False,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
                scalar=1,
            )  # compute n = l2*conj(l2)

            out += Script.parse_string("OP_TOALTSTACK OP_2ROT")
            shift_val = (
                3 * extension_degree
                - (3 * extension_degree if is_t_rolled else 0)
                - (2 * extension_degree if not is_tangent and is_q_rolled else 0)
            )

            out += move(P.x.shift(shift_val), moving_function=bool_to_moving_function(is_p_rolled))

            out += Script.parse_string("OP_SUB")  # compute xQ - xP * u

            out += self.fq2.mul(
                take_modulo=False, check_constant=False, clean_constant=False
            )  # compute m * (xQ - xP * u)
            out += Script.parse_string("OP_2SWAP OP_FROMALTSTACK OP_DUP OP_TOALTSTACK")
            out += self.fq2.base_field_scalar_mul(
                take_modulo=False,
                check_constant=False,
                clean_constant=False,
            )  # compute yQ * n

            out += self.fq2.subtract(
                take_modulo=take_modulo,
                positive_modulo=positive_modulo,
                check_constant=False,
                clean_constant=False,
                is_constant_reused=False,
            )  # compute A = - yQ * n + m * (xQ - xP * u)
            shift_val = (
                extension_degree
                - (3 * extension_degree if is_t_rolled else 0)
                - (2 * extension_degree if not is_tangent and is_q_rolled else 0)
            )

            out += move(P.y.shift(shift_val), moving_function=bool_to_moving_function(is_p_rolled))

            out += Script.parse_string("OP_FROMALTSTACK OP_TUCK OP_MUL")  # compute B = yP * n

            if take_modulo:
                out += pick(position=-1, n_elements=1) if not clean_constant else roll(position=-1, n_elements=1)
                out += mod(
                    stack_preparation="",
                    is_mod_on_top=True,
                    is_positive=positive_modulo,
                    is_constant_reused=True,
                )
                out += mod(
                    stack_preparation="OP_ROT OP_ROT",
                    is_mod_on_top=True,
                    is_positive=positive_modulo,
                    is_constant_reused=is_constant_reused,
                )
            else:
                out += Script.parse_string("OP_SWAP")

        return out


line_functions = LineFunctions(fq2=fq2_script)

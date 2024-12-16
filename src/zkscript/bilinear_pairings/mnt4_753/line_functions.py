"""Bitcoin scripts that perform line evaluation for MNT4-753."""

from tx_engine import Script

from src.zkscript.bilinear_pairings.mnt4_753.fields import fq2_script
from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import bitmask_to_boolean_list, check_order
from src.zkscript.util.utility_scripts import bool_to_moving_function, mod, move, pick, roll, verify_bottom_constant


class LineFunctions:
    """Line evaluation for MNT4-753."""

    def __init__(self, fq2):
        """Initialise line evaluation for MNT4-753.

        Args:
            fq2 (Fq2): Bitcoin script instance to perform arithmetic operations in F_q^2.
        """
        self.MODULUS = fq2.MODULUS
        self.FQ2 = fq2

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

        Notes:
            - `gradient` is NOT checked in this function, it is assumed to be the gradient.
            - `ev_(l_(T,Q)(P))` does NOT include the zero in the second component, this is to optimise the script size.
        """
        # Fq2 implementation
        fq2 = self.FQ2

        check_order([gradient, P, Q])
        is_gradient_rolled, is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Line evaluation for MNT4 returns: (gradient, Q, P) --> (-yQ + gradient * (xQ - xP*u), yP) as a point in Fq4

        # Compute -yQ + gradient * (xQ - xP*u)
        # stack in:  [q .. gradient .. P .. Q ..]
        # stack out: [q .. gradient ..{xP} yP .. {xQ} yQ .. (xQ - xP*u)]
        first_component = move(Q.x, bool_to_moving_function(is_q_rolled))  # Move xQ
        first_component += move(P.x.shift(2 - 2 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move xP
        first_component += Script.parse_string("OP_SUB")
        # stack in:  [q .. gradient ..{xP} yP .. {xQ} yQ .. (xQ - xP*u)]
        # stack out: [q .. {gradient} .. {xP} yP .. {xQ} yQ .. gradient * (xQ - xP*u)]
        first_component += move(
            gradient.shift(2 - 2 * is_q_rolled - 1 * is_p_rolled), bool_to_moving_function(is_gradient_rolled)
        )  # Move gradient
        first_component += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        # stack in:     [q .. {gradient} .. {xP} yP .. {xQ} yQ .. gradient * (xQ - xP*u)]
        # stack out:    [q .. {gradient} .. {xP} yP .. {xQ} {yQ} .. (-yQ + lambda * (xQ - xP*u))_0]
        # altstack out: [(-yQ + lambda * (xQ - xP*u))_1]
        first_component += move(Q.y.shift(2), bool_to_moving_function(is_q_rolled), 1, 2)  # Move (yQ)_1
        if Q.negate:
            first_component += Script.parse_string("OP_ADD OP_TOALTSTACK")
        else:
            first_component += Script.parse_string("OP_SUB OP_TOALTSTACK")
        first_component += move(
            Q.y.shift(1 - 1 * is_q_rolled), bool_to_moving_function(is_q_rolled), 0, 1
        )  # Move (yQ)_0
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
            out += move(P.y.shift(3 - 4 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move yP
            out += Script.parse_string("OP_ROT")
            out += mod(stack_preparation="", is_constant_reused=is_constant_reused, is_positive=positive_modulo)
        else:
            out += Script.parse_string("OP_FROMALTSTACK")
            out += move(P.y.shift(2 - 4 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move yP

        return out


line_functions = LineFunctions(fq2=fq2_script)

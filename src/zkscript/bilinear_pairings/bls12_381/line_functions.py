"""Bitcoin scripts that perform line evaluation for BLS12-381."""

from tx_engine import Script

from src.zkscript.bilinear_pairings.bls12_381.fields import fq2_script
from src.zkscript.fields.fq2 import Fq2
from src.zkscript.script_types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import bitmask_to_boolean_list, check_order
from src.zkscript.util.utility_scripts import bool_to_moving_function, mod, move, pick, roll, verify_bottom_constant


class LineFunctions:
    """Line evaluation for BLS12-381."""

    def __init__(self, fq2: Fq2):
        """Initialise line evaluation for BLS12-381.

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
            - stack:    [q, ..., gradient, .., P, .., Q, ..], `P` is in `E(F_q)`, `Q` is in `E'(F_q^2)`,
                the sextic twist, `gradient` is in F_q^2
            - altstack: []

        Stack output:
            - stack:    [q, ..., ev_(l_(T,Q)(P))], `ev_(l_(T,Q))(P)` is an element in F_q^12, the cubic extension of
                F_q^4
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
        check_order([gradient, P, Q])
        is_gradient_rolled, is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # For BLS12 M-twist, the line function returns:
        # (gradient, P, Q) --> -yQ + gradient*xQ + yp * s - gradient * xP * r^2

        # Compute - gradient * xP
        # stack in:     [q .. gradient .. P .. Q ..]
        # stack out:    [q .. {gradient} .. {xP} yP .. Q .. gradient_1 gradient_0]
        # altstack out: [-gradient*xP]
        third_component = move(gradient, bool_to_moving_function(is_gradient_rolled), 1, 2)  # Move gradient_1
        third_component += move(P.x.shift(1), bool_to_moving_function(is_p_rolled))  # Move xP
        third_component += Script.parse_string("OP_NEGATE")  # Negate xP
        third_component += Script.parse_string(
            "OP_TUCK OP_OVER OP_MUL"
        )  # Duplicate xP, gradient_1, compute -xP*gradient_1
        third_component += Script.parse_string("OP_ROT")  # Rotate -xP
        third_component += move(
            gradient.shift(3 - 1 * is_p_rolled - 1 * is_gradient_rolled),
            bool_to_moving_function(is_gradient_rolled),
            0,
            1,
        )  # Move gradient_0
        third_component += Script.parse_string("OP_TUCK OP_MUL OP_ROT")  # Duplicate gradient_0, compute xP * gradient_0
        third_component += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Compute -yQ + lmabda*xQ
        # stack in:     [q .. {gradient} .. {xP} yP .. Q .. gradient_1 gradient_0]
        # altstack in:  [-gradient*xP]
        # stack out:    [q .. {gradient} .. {xP} yP .. {Q} .. (-yQ + gradient*xQ)_0]
        # altstack out: [-gradient*xP, (-yQ + gradient*xQ)_1]
        first_component = Script.parse_string("OP_SWAP")  # Reorder gradient
        first_component += move(Q.x.shift(2), bool_to_moving_function(is_q_rolled))  # Move xQ
        first_component += self.fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute xQ*gradient
        first_component += move(Q.y.shift(2), bool_to_moving_function(is_q_rolled), 1, 2)  # Move yQ_1
        if Q.negate:
            first_component += Script.parse_string("OP_ADD OP_TOALTSTACK")
        else:
            first_component += Script.parse_string("OP_SUB OP_TOALTSTACK")
        first_component += move(Q.y.shift(1 - 1 * is_q_rolled), bool_to_moving_function(is_q_rolled), 0, 1)  # Move yQ_0
        if Q.negate:
            first_component += Script.parse_string("OP_ADD")
        else:
            first_component += Script.parse_string("OP_SUB")

        out += third_component + first_component

        if take_modulo:
            out += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_mod_on_top=True, is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo)
            out += move(P.y.shift(3 - 4 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move yP
            out += Script.parse_string("OP_ROT")  # Rotate q
            out += mod(stack_preparation="", is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo)
            out += mod(is_constant_reused=is_constant_reused, is_positive=positive_modulo)
        else:
            out += Script.parse_string("OP_FROMALTSTACK")
            out += move(P.y.shift(2 - 2 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move yP
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")

        return out


line_functions = LineFunctions(fq2=fq2_script)

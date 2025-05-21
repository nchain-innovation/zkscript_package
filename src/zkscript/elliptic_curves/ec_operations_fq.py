"""Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q)."""

from math import ceil, log2

from tx_engine import Script

from src.zkscript.script_types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement, StackNumber
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


class EllipticCurveFq:
    """Construct Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q).

    Arithmetic is performed in affine coordinates. Points are represented on the stack as a list of two
    numbers: P := [x, y], except for the point at infinity, which is encoded as [0x00, 0x00]. Note that
    the points are 0x00, not OP_0.

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

    def evaluate_curve_equation(
        self,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_option: bool = True,
    ) -> Script:
        """Evaluate the curve equation on P.

        This scripts computes (y_P^2 - x_P^3 + self.a * x_P + self.b mod self.modulus) and leaves it on the stack.

        Stack input:
            - stack:    [q, .., P, ..]
            - altstack: []
        Stack output:
            - stack:    [q, .., P, .., (y_P^2 - x_P^3 + self.a * x_P + self.b mod self.modulus)]
            - altstack: []

        Args:
            check_constant (bool | None): If `True`, check if `modulus` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `modulus` from the bottom of the stack. Defaults to `None`.
            modulus: The position of `self.modulus` in the stack.
            P (StackEllipticCurvePoint): The position in the stack of the point `P` for which the script
                checks whether `P` belongs to the curve. Defaults to:
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(1, False, 1),
                    StackFiniteFieldElement(0, False, 1),
                )`
            rolling_option (bool): If `True`, `P` is removed from the stack after the execution of the script.
                Defaults to `True`.
        """
        if modulus.position > 0:
            check_order([modulus, P])

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        out += move(P, bool_to_moving_function(rolling_option))  # Move P
        out += Script.parse_string("OP_DUP OP_MUL")  # Compute y_P^2
        out += Script.parse_string("OP_OVER" if self.curve_a else "OP_SWAP")
        out += Script.parse_string("OP_DUP OP_DUP OP_MUL OP_MUL OP_SUB")  # Compute y_P^2 - x_P^3
        if self.curve_a:
            out += (
                Script.parse_string("OP_SWAP") + nums_to_script([self.curve_a]) + Script.parse_string("OP_MUL OP_SUB")
            )  # Compute y_P^2 - x_P^3 - self.curve_a * x_P
        # Compute y_P^2 - x_P^3 - self.curve_a * x_P - self.curve_b
        match self.curve_b:
            case 1:
                out += Script.parse_string("OP_1SUB")
            case -1:
                out += Script.parse_string("OP_1ADD")
            case 0:
                pass
            case _:
                out += nums_to_script([self.curve_b]) + Script.parse_string("OP_SUB")
        out += move(
            modulus.shift(1 - 2 * rolling_option if modulus.position > 0 else 0),
            bool_to_moving_function(clean_constant),
        )
        out += mod(stack_preparation="", is_positive=False, is_constant_reused=False)

        return out

    def is_on_curve(
        self,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_option: bool = True,
    ) -> Script:
        """Verify that P is on the curve.

        This script verifies that P is on the curve. Namely, that
            y_P^2 = x_P^3 + self.a * x_P + self.b mod self.modulus.

        Stack input:
            - stack:    [q, .., P, ..]
            - altstack: []
        Stack output:
            - stack:    [q, .., P, ..] or fail
            - altstack: []

        Args:
            check_constant (bool | None): If `True`, check if `modulus` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `modulus` from the bottom of the stack. Defaults to `None`.
            modulus (StackNumber): The position of `self.modulus` in the stack.
            P (StackEllipticCurvePoint): The position in the stack of the point `P` for which the script
                checks whether `P` belongs to the curve. Defaults to:
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(1, False, 1),
                    StackFiniteFieldElement(0, False, 1),
                )`
            rolling_option (bool): If `True`, `P` is removed from the stack after the execution of the script.
                Defaults to `True`.

        Returns:
            The script that verifies that `P` is on the curve.
        """
        out = self.evaluate_curve_equation(
            check_constant=check_constant,
            clean_constant=clean_constant,
            modulus=modulus,
            P=P,
            rolling_option=rolling_option,
        )
        out += is_equal_to(target=0)

        return out

    def point_algebraic_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        positive_modulo: bool = True,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(4, False, 1),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 1),  # noqa: B008
            StackFiniteFieldElement(2, False, 1),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        The function branches according to the value of verify_gradient.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [.., q, .., gradient, .., P, .., Q, ..]
            - altstack = []

        Stack output:
            - stack    = [.., q, .., gradient, .., P, .., Q, .., (P_+ Q_)]
            - altstack = []

        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulus (StackNumber): The position of `self.modulus` in the stack.
            gradient (StackFiniteFieldElement): The position of gradient through P_ and Q_ in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackFiniteFieldElement(4,False,1)
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(3,False,1),StackFiniteFieldElement(2,False,1)
                    )
            Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(1,False,1),StackFiniteFieldElement(0,False,1)
                    )
            rolling_options (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 7 (all elements are rolled).


        Returns:
            A Bitcoin Script that computes P_ + Q_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `gradient` comes after `P` in the stack
                - `P` comes after `Q` in the stack

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` != `Q_` and `P_ != -Q_` and `P_`, `Q_` not the point at infinity
        """
        check_order([gradient, P, Q])
        return (
            self.__point_algebraic_addition_verifying_gradient(
                take_modulo, check_constant, clean_constant, positive_modulo, modulus, gradient, P, Q, rolling_options
            )
            if verify_gradient
            else self.__point_algebraic_addition_without_verifying_gradient(
                take_modulo, check_constant, clean_constant, positive_modulo, modulus, gradient, P, Q, rolling_options
            )
        )

    def point_algebraic_doubling(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        positive_modulo: bool = True,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 3,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        The function branches according to the value of verify_gradient.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [q, .., gradient, .., P, .., 2P_]
            - altstack = []

        P_ = -P not P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulus (StackNumber): The position of `self.modulus` in the stack. Defaults to `StackNumber(-1, False)`.
            gradient (StackFiniteFieldElement): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackFiniteFieldElement(2,False,1,roll).
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackEllipticCurvePoint(
                        StackFiniteFieldElement(1,False,1),StackFiniteFieldElement(0,False,1)
                        )
            rolling_options (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 3 (all elements are rolled).

        Returns:
            A Bitcoin Script that computes 2P_ for the given elliptic curve points `P`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `gradient` comes after `P` in the stack

        Preconditions:
            - The input point `P` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P` not the point at infinity
        """
        check_order([gradient, P])
        return (
            self.__point_algebraic_doubling_verifying_gradient(
                take_modulo, check_constant, clean_constant, positive_modulo, modulus, gradient, P, rolling_options
            )
            if verify_gradient
            else self.__point_algebraic_doubling_without_verifying_gradient(
                take_modulo, check_constant, clean_constant, positive_modulo, modulus, gradient, P, rolling_options
            )
        )

    def __point_algebraic_addition_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(4, False, 1),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 1),  # noqa: B008
            StackFiniteFieldElement(2, False, 1),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, .., Q, ..]
            - altstack = []

        Stack output:
            - stack    = [q, .., gradient, .., P, .., Q, .., (P_+ Q_)]
            - altstack = []

        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulus (StackNumber): The position of `self.modulus` in the stack. Defaults to `StackNumber(-1, False)`.
            gradient (StackFiniteFieldElement): The position of gradient through P_ and Q_ in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackFiniteFieldElement(4,False,1)
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(3,False,1),StackFiniteFieldElement(2,False,1)
                    )
            Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(1,False,1),StackFiniteFieldElement(0,False,1)
                    )
            rolling_options (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 7 (all elements are rolled).

        Returns:
            A Bitcoin Script that computes P_ + Q_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `gradient` comes after `P` in the stack
                - `P` comes after `Q` in the stack

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` and `Q_` are not equal, nor inverse, nor the point at infinity

        Notes:
            If this function is used when `P_` != `Q_` or `P_ != -Q_`, then any gradient will pass
            the gradient verification, but the point computed is not going to be `P_ + Q_`.
        """
        is_gradient_rolled, is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Write:
        #   P_ = -P not P.y.negate else P
        #   Q_ = -Q if Q.y.negate else Q

        # Verify that gradient is the gradient between P_ and Q_
        # stack in:     [q, .., gradient, .., P, .., Q, ..]
        # stack out:    [q, .., gradient, .., P, .., Q, .., yP, xQ, xP, gradient, or fail]
        # Altstack out: [q, if take_modulo]
        verify_gradient = move(Q, bool_to_moving_function(is_q_rolled))  # Move xQ, yQ
        verify_gradient += move(P.y.shift(2 - 2 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move yP
        verify_gradient += Script.parse_string("OP_TUCK")
        if (P.negate and not Q.negate) or (not P.negate and Q.negate):
            verify_gradient += Script.parse_string("OP_ADD")  # Compute yQ + yP
        else:
            verify_gradient += Script.parse_string("OP_SUB")  # Compute yQ - yP
        verify_gradient += roll(position=2, n_elements=1)  # Bring xQ on top
        verify_gradient += move(
            P.x.shift(3 - 2 * is_q_rolled - 1 * is_p_rolled), bool_to_moving_function(is_p_rolled)
        )  # Move xP
        verify_gradient += Script.parse_string("OP_2DUP OP_SUB")  # Duplicate xP, xQ, compute xQ - xP
        verify_gradient += move(
            gradient.shift(5 - 2 * is_p_rolled - 2 * is_q_rolled), bool_to_moving_function(is_gradient_rolled)
        )  # Move gradient
        verify_gradient += Script.parse_string("OP_TUCK OP_MUL")  # Compute gradient *(xP - xQ)
        verify_gradient += roll(position=4, n_elements=1)  # Bring yQ + yP or yQ - yP on top
        if (P.negate and not Q.negate) or (not P.negate and not Q.negate):
            verify_gradient += Script.parse_string("OP_SUB")  # Compute gradient *(xP - xQ) - (yP_ - yQ_)
        else:
            verify_gradient += Script.parse_string("OP_ADD")  # Compute gradient *(xP - xQ) - (yP_ - yQ_)
        verify_gradient += move(modulus, bool_to_moving_function(clean_constant))
        verify_gradient += mod(stack_preparation="", is_positive=False)
        verify_gradient += Script.parse_string("OP_0 OP_EQUALVERIFY")
        verify_gradient += Script.parse_string("OP_TOALTSTACK" if take_modulo else "OP_DROP")

        # Compute x(P_+Q_) = gradient^2 - x_P - x_Q
        # stack in:     [q, .., gradient, .., P, .., Q, .., yP, xQ, xP, gradient]
        # Altstack in:  [q, if take_modulo]
        # stack out:    [q, .., gradient, .., P, .., Q, .., yP, gradient, x(P_+Q_)]
        # Altstack out: [q, if take_modulo, xP]
        x_coordinate = Script.parse_string("OP_DUP OP_DUP OP_MUL")  # Duplicate gradient and compute gradient^2
        x_coordinate += Script.parse_string("OP_2SWAP OP_TUCK")  # Swap gradient, gradient^2 and xQ, xP, duplicate xP
        x_coordinate += Script.parse_string(
            "OP_TOALTSTACK OP_ADD OP_SUB"
        )  # Put xP on altstack, compute gradient^2 - (xQ + xP)

        # Compute y(P_+Q_) = gradient * (xP - x(P_+Q_)) - yP_
        # stack in:     [q, .., gradient, .., P, .., Q, .., yP, gradient, x(P_+Q_)]
        # Altstack in:  [q, if take_modulo, xP]
        # stack out:    [q, .., gradient, .., P, .., Q, .., x(P_+Q_), y(P_+Q_)]
        # Altstack out: []
        y_coordinate = Script.parse_string("OP_FROMALTSTACK")  # Pull xP from altstack
        y_coordinate += pick(position=1, n_elements=1)  # Duplicate x(P_+Q_)
        y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=2, n_elements=1)  # Bring gradient on top
        y_coordinate += Script.parse_string("OP_MUL")  # Compute gradient * (xP - x(P_+Q_))
        y_coordinate += roll(position=2, n_elements=1)  # Bring yP on top
        y_coordinate += Script.parse_string("OP_ADD" if P.y.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += mod(stack_preparation="OP_FROMALTSTACK", is_positive=positive_modulo)
            y_coordinate += mod(
                stack_preparation="OP_TOALTSTACK", is_constant_reused=False, is_positive=positive_modulo
            )
            y_coordinate += Script.parse_string("OP_FROMALTSTACK")

        out += verify_gradient + x_coordinate + y_coordinate
        return out

    def __point_algebraic_addition_without_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(4, False, 1),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 1),  # noqa: B008
            StackFiniteFieldElement(2, False, 1),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        This functions does not verify the validity of the gradient provided.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, .., Q, ..]
            - altstack = []

        Stack output:
            - stack    = [q, .., gradient, .., P, .., Q, .., (P_+ Q_)]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulus (StackNumber): The position of `self.modulus` in the stack. Defaults to `StackNumber(-1, False)`.
            gradient (StackFiniteFieldElement): The position of gradient through P_ and Q_ in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackFiniteFieldElement(4,False,1)
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(3,False,1),StackFiniteFieldElement(2,False,1)
                    )
            Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(1,False,1),StackFiniteFieldElement(0,False,1)
                    )
            rolling_options (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 7 (all elements are rolled).

        Returns:
            A Bitcoin Script that computes P_ + Q_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `gradient` comes after `P` in the stack
                - `P` comes after `Q` in the stack

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` and `Q_` are not equal, nor inverse, nor the point at infinity
        """
        is_gradient_rolled, is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Write:
        #   P_ = -P not P.y.negate else P
        #   Q_ = -Q if Q.y.negate else Q

        drop_yq = move(Q.y, bool_to_moving_function(is_q_rolled))  # Move yQ
        drop_yq += Script.parse_string("OP_DROP")
        if is_q_rolled:
            out += drop_yq

        # Compute x(P_+Q_) = gradient^2 - x_P - x_Q
        # stack in:  [q, .., gradient, .., P, .., Q, ..]
        # stack out: [q, .., gradient, .., P, .., Q, ..,  xP, gradient, x(P_+Q_)]
        x_coordinate = move(Q.x.shift(-1 * is_q_rolled), bool_to_moving_function(is_q_rolled))  # Move xQ
        x_coordinate += move(P.x.shift(1 - 2 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move xP
        x_coordinate += Script.parse_string("OP_TUCK OP_ADD")  # Duplicate xP, compute xP + xQ
        x_coordinate += move(
            gradient.shift(2 - 2 * is_q_rolled - 1 * is_p_rolled), bool_to_moving_function(is_gradient_rolled)
        )  # Move gradient
        x_coordinate += Script.parse_string("OP_DUP OP_DUP OP_MUL")  # Duplicate almbda, compute gradient^2
        x_coordinate += roll(position=2, n_elements=1)  # Bring xP + xQ on top
        x_coordinate += Script.parse_string("OP_SUB")  # Compute gradient^2 - (xP + xQ)

        # Compute y(P_+Q_) = gradient * (xP - x(P_+Q_)) - yP_
        # stack in:  [q, .., gradient, .., P, .., Q, ..,  xP, gradient, x(P_+Q_)]
        # stack out: [q, .., gradient, .., P, .., Q, .., x(P_+Q_), y(P_+Q_)]
        y_coordinate = roll(position=2, n_elements=1)  # Bring xP on top
        y_coordinate += pick(position=1, n_elements=1)  # Duplicate x(P_+Q_)
        y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=2, n_elements=1)  # Bring gradient on top
        y_coordinate += Script.parse_string("OP_MUL")  # Compute gradient * (xP - x(P_+Q_))
        y_coordinate += move(P.y.shift(2 - 2 * is_q_rolled), bool_to_moving_function(is_p_rolled))  # Move yP
        y_coordinate += Script.parse_string("OP_ADD" if P.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += Script.parse_string("OP_TOALTSTACK")
            y_coordinate += move(modulus, bool_to_moving_function(clean_constant))
            y_coordinate += mod(stack_preparation="", is_positive=positive_modulo)
            y_coordinate += mod(is_constant_reused=False, is_positive=positive_modulo)

        out += x_coordinate + y_coordinate
        return out

    def __point_algebraic_doubling_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 3,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [q, .., gradient, .., P, .., 2P_]
            - altstack = []

        P_ = -P not P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulus (StackNumber): The position of `self.modulus` in the stack. Defaults to `StackNumber(-1, False)`.
            gradient (StackFiniteFieldElement): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackFiniteFieldElement(2,False,1).
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackEllipticCurvePoint(
                        StackFiniteFieldElement(1,False,1),StackFiniteFieldElement(0,False,1)
                        )
            rolling_options (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 3 (all elements are rolled).

        Returns:
            A Bitcoin Script that computes 2P_ for the given elliptic curve points `P`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `gradient` comes after `P` in the stack

        Preconditions:
            - The input point `P` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P` not the point at infinity
        """
        is_gradient_rolled, is_p_rolled = bitmask_to_boolean_list(rolling_options, 2)

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        curve_a = self.curve_a

        # Verify that gradient is the gradient between P_ and Q_
        # stack in:     [q, .., gradient, .., P, ..]
        # stack out:    [q, .., gradient, .., P, .., xP, yP, gradient, or fail]
        # Altstack out: [q, if take_modulo]
        verify_gradient = move(P, bool_to_moving_function(is_p_rolled))  # Move xP, yP
        verify_gradient += pick(position=1, n_elements=2)  # Duplicate xP, yP
        verify_gradient += Script.parse_string("OP_2 OP_MUL")  # Compute 2yP
        verify_gradient += move(
            gradient.shift(4 - 2 * is_p_rolled), bool_to_moving_function(is_gradient_rolled)
        )  # Move gradient
        verify_gradient += Script.parse_string("OP_TUCK")  # Duplicate gradient
        verify_gradient += Script.parse_string("OP_MUL")  # Compute 2yP * gradient
        verify_gradient += roll(position=2, n_elements=1)  # Bring xP on top
        verify_gradient += Script.parse_string("OP_DUP OP_MUL")  # Compute xP^2
        verify_gradient += Script.parse_string("OP_3 OP_MUL")  # Compute 3*xP^2
        if curve_a:
            verify_gradient += nums_to_script([curve_a])
            verify_gradient += Script.parse_string("OP_ADD")
        verify_gradient += Script.parse_string("OP_ADD" if P.y.negate else "OP_SUB")
        verify_gradient += move(modulus, bool_to_moving_function(clean_constant))
        verify_gradient += mod(stack_preparation="", is_positive=False)
        verify_gradient += Script.parse_string("OP_0 OP_EQUALVERIFY")
        verify_gradient += Script.parse_string("OP_TOALTSTACK" if take_modulo else "OP_DROP")

        # Compute x(P_+Q_) = gradient^2 - 2*x_P
        # stack in:     [q, .., gradient, .., P, .., xP, yP, gradient]
        # Altstack in:  [q, if take_modulo]
        # stack out:    [q, .., gradient, .., P, .., Q, ..,  gradient, xP, x(P_+Q_)]
        # Altstack out: [q, if take_modulo, yP]
        x_coordinate = Script.parse_string("OP_DUP OP_DUP OP_MUL")  # Duplicate gradient, compute gradient^2
        x_coordinate += roll(position=3, n_elements=2)  # Bring xP, yP on top
        x_coordinate += Script.parse_string("OP_TOALTSTACK")  # Put yP on altstack
        x_coordinate += Script.parse_string("OP_TUCK")  # Duplicate xP
        x_coordinate += Script.parse_string("OP_2 OP_MUL OP_SUB")  # Compute gradient^2 - 2*x_P

        # Compute x(P_+Q_) = gradient^2 - 2*x_P
        # stack in:     [q, .., gradient, .., P, ..,  gradient, xP, x(P_+Q_)]
        # Altstack in:  [q, if take_modulo, yP]
        # stack out:    [q, .., gradient, .., P, ..,  x(P_+Q_), y(P_+Q_)]
        # Altstack out: []
        y_coordinate = roll(position=1, n_elements=1)  # Bring xP on top
        y_coordinate += pick(position=1, n_elements=1)  # Duplicate x(P_+Q_)
        y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=2, n_elements=1)  # Bring gradient on top
        y_coordinate += Script.parse_string("OP_MUL")  # Compute gradient * (xP - x(P_+Q_))
        y_coordinate += Script.parse_string("OP_FROMALTSTACK")  # Pull yP from altstack
        y_coordinate += Script.parse_string("OP_ADD" if P.y.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += mod(stack_preparation="OP_FROMALTSTACK", is_positive=positive_modulo)
            y_coordinate += mod(
                stack_preparation="OP_TOALTSTACK", is_constant_reused=False, is_positive=positive_modulo
            )
            y_coordinate += Script.parse_string("OP_FROMALTSTACK")

        out += verify_gradient + x_coordinate + y_coordinate
        return out

    def __point_algebraic_doubling_without_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
        modulus: StackNumber = StackNumber(-1, False),  # noqa: B008
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 3,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        This function does not verify the validity of the gradient provided.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., {gradient}, .., {P}, .., 2P_]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            modulus (StackNumber): The position of `self.modulus` in the stack. Defaults to `StackNumber(-1, False)`.
            gradient (StackFiniteFieldElement): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackFiniteFieldElement(2,False,1).
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackEllipticCurvePoint(
                        StackFiniteFieldElement(1,False,1),StackFiniteFieldElement(0,False,1)
                        )
            rolling_options (int): A bitmask specifying which arguments should be rolled on which should
                be picked. The bits of the bitmask correspond to whether the i-th argument should be
                rolled or not. Defaults to 3 (all elements are rolled).

        Returns:
            A Bitcoin Script that computes 2P_ for the given elliptic curve points `P`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `gradient` comes after `P` in the stack

        Preconditions:
            - The input point `P` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P` not the point at infinity
        """
        is_gradient_rolled, is_p_rolled = bitmask_to_boolean_list(rolling_options, 2)

        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # Compute x(P_+Q_) = gradient^2 - 2*x_P
        # stack in:  [q, .., gradient, .., P, ..]
        # stack out: [q, .., gradient, .., P, ..,  xP, yP, gradient, x(2P_)]
        x_coordinate = move(P, bool_to_moving_function(is_p_rolled))  # Move xP, yP
        x_coordinate += Script.parse_string("OP_OVER OP_2 OP_MUL")  # Duplicate xP, compute 2xP
        x_coordinate += move(
            gradient.shift(3 - 2 * is_p_rolled), bool_to_moving_function(is_gradient_rolled)
        )  # Move gradient
        x_coordinate += Script.parse_string("OP_TUCK OP_DUP OP_MUL")  # Duplicate gradient, compute lamdba^2
        x_coordinate += Script.parse_string("OP_SWAP OP_SUB")  # Compute gradient^2 - 2*x_P

        # Compute y(P_+Q_) = gradient * (xP - x(P_+Q_)) - yP_
        # stack in:  [q, .., gradient, .., P, ..,  xP, yP, gradient, x(2P_)]
        # stack out: [q, .., gradient, .., P, .., Q, ..,  x(P_+Q_), y(P_+Q_)]
        y_coordinate = roll(position=3, n_elements=1)  # Bring xP on top
        y_coordinate += pick(position=1, n_elements=1)  # Duplicate x(P_+Q_)
        y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=2, n_elements=1)  # Bring gradient on top
        y_coordinate += Script.parse_string("OP_MUL")  # Compute gradient * (xP - x(P_+Q_))
        y_coordinate += roll(position=2, n_elements=1)  # Pull yP from altstack
        y_coordinate += Script.parse_string("OP_ADD" if P.y.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += Script.parse_string("OP_TOALTSTACK")
            y_coordinate += move(modulus, bool_to_moving_function(clean_constant))
            y_coordinate += mod(stack_preparation="", is_positive=positive_modulo)
            y_coordinate += mod(is_constant_reused=False, is_positive=positive_modulo)

        out += x_coordinate + y_coordinate
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
            - stack    = [q, .., gradient, P, Q]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., (P + Q)]
            - altstack = []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            A Bitcoin script that compute the sum of `P` and `Q`, handling all possibilities.

        Preconditions:
            - P and Q are points on E(F_q)
            - If P != -Q, then gradient is the gradient of the line through P and Q
            - If P = -Q or P is the point at infinity, or Q is the point at infinity, then do not put gradient

        Notes:
            If P = -Q, then we return 0x00 0x00, i.e., we encode the point at infinity as (0x00,0x00) (notice that
            these are data payloads, they are not numbers - points are assumed to be passed as numbers, which means that
            (0,0) would have to be passed as OP_0 OP_0)
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        curve_a = self.curve_a

        # Check if Q or P is point at infinity or if P = - Q -----------------------------------------------------------
        # After this, the stack is: gradient P Q

        # Check if Q is (0x00,0x00), in that case, terminate and return P
        out += Script.parse_string("OP_2DUP OP_CAT 0x0000 OP_EQUAL OP_NOT")
        out += Script.parse_string("OP_IF")

        # Check if P is (0x00,0x00), in that case, terminate and return Q
        out += Script.parse_string("OP_2OVER OP_CAT 0x0000 OP_EQUAL OP_NOT")
        out += Script.parse_string("OP_IF")

        # Check if P = -Q, in that case terminate and return (0x00,0x00)
        out += Script.parse_string("OP_DUP")  # Duplicate yQ
        out += pick(position=3, n_elements=1)  # Pick yP
        out += Script.parse_string("OP_ADD")
        out += Script.parse_string("OP_DEPTH OP_1SUB OP_PICK OP_MOD OP_0NOTEQUAL")
        out += Script.parse_string("OP_IF")

        # End of initial checks  ---------------------------------------------------------------------------------------

        # Validate gradient --------------------------------------------------------------------------------------------
        # After this, the stack is: gradient P Q, altstack = [Verify(gradient)]

        # Check if P = Q:
        out += Script.parse_string("OP_2OVER OP_2OVER")  # Roll P and Q
        out += Script.parse_string("OP_CAT")  # Concatenate xQ||yQ
        out += Script.parse_string("OP_ROT OP_ROT")  # Rotate xP and xQ
        out += Script.parse_string("OP_CAT")  # Concatenate xP||yP
        out += Script.parse_string("OP_EQUAL")  # Check xP||yP = xQ||yQ

        # If P = Q:
        out += Script.parse_string("OP_IF")
        out += Script.parse_string("OP_DUP")  # Duplicate y_P
        out += Script.parse_string("OP_2 OP_MUL")  # Compute 2y_P
        out += pick(position=3, n_elements=1)  # Pick gradient
        out += Script.parse_string("OP_MUL")  # Compute 2 gradient y_P
        out += pick(position=2, n_elements=1)  # Pick x_P
        out += Script.parse_string("OP_DUP")  # Duplicate x_P
        out += Script.parse_string("OP_MUL")  # Compute x_P^2
        out += Script.parse_string("OP_3 OP_MUL")  # Compute 3 x_P^2
        if curve_a != 0:
            out += nums_to_script([curve_a]) + Script.parse_string("OP_ADD")  # Compute 3 x_P^2 + a if a != 0
        out += Script.parse_string("OP_SUB")

        # If P != Q:
        out += Script.parse_string("OP_ELSE")
        out += pick(position=4, n_elements=2)  # Pick gradient and x_P
        out += Script.parse_string("OP_MUL OP_ADD")  # compute gradient x_P + y_Q
        out += Script.parse_string("OP_OVER OP_5 OP_PICK OP_MUL OP_3 OP_PICK OP_ADD")  # compute gradient x_Q + y_P
        out += Script.parse_string("OP_SUB")
        out += Script.parse_string("OP_ENDIF")

        # Place on the altstack
        out += Script.parse_string("OP_TOALTSTACK")

        # End of gradient validation -----------------------------------------------------------------------------------

        # Calculation of P + Q
        # After this, the stack is: (P+Q), altstack = [Verify(gradient)]

        # Compute x_(P+Q) = gradient^2 - x_P - x_Q
        # After this, the base stack is: gradient x_P y_P x_(P+Q), altstack = [Verify(gradient)]
        compute_x_coordinate = Script.parse_string("OP_2OVER")
        compute_x_coordinate += Script.parse_string("OP_SWAP")
        compute_x_coordinate += Script.parse_string("OP_DUP OP_MUL")  # Compute gradient^2
        compute_x_coordinate += Script.parse_string("OP_ROT OP_ROT OP_ADD OP_SUB")  # Compute gradient^2 - (x_P + x_Q)

        # Compute y_(P+Q) = gradient (x_P - x_(P+Q)) - y_P
        # After this, the stack is: x_(P+Q) y_(P+Q), altstack = [Verify(gradient)]
        compute_y_coordinate = Script.parse_string("OP_TUCK")
        compute_y_coordinate += Script.parse_string("OP_2SWAP")
        compute_y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x_(P+Q)
        compute_y_coordinate += Script.parse_string("OP_2SWAP OP_TOALTSTACK")
        compute_y_coordinate += Script.parse_string(
            "OP_MUL OP_FROMALTSTACK OP_SUB"
        )  # Compute gradient (x_P - x_(P+Q)) - y_P

        # After this, the stack is: (P+Q), altstack = [Verify(gradient)]
        out += compute_x_coordinate + compute_y_coordinate

        if take_modulo:
            out += Script.parse_string("OP_TOALTSTACK")
            out += pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_mod_on_top=True, is_positive=positive_modulo, is_constant_reused=True)
            out += mod(is_positive=positive_modulo, is_constant_reused=False)

        verify_gradient = Script.parse_string("OP_FROMALTSTACK")
        verify_gradient += mod(
            stack_preparation="OP_DEPTH OP_1SUB OP_PICK",
            is_mod_on_top=True,
            is_constant_reused=False,
            is_positive=False,
        )
        verify_gradient += Script.parse_string("OP_0 OP_EQUALVERIFY")

        # Check gradient was correct
        out += verify_gradient

        # Termination conditions  --------------------------------------------------------------------------------------

        # Termination because P = -Q
        out += Script.parse_string("OP_ELSE")
        out += Script.parse_string("OP_2DROP OP_2DROP")
        out += Script.parse_string("0x00 0x00")
        out += Script.parse_string("OP_ENDIF")

        # Termination because P = (0x00,0x00)
        out += Script.parse_string("OP_ELSE")
        out += Script.parse_string("OP_2SWAP OP_2DROP")
        out += Script.parse_string("OP_ENDIF")

        # Termination because Q = (0x00,0x00)
        out += Script.parse_string("OP_ELSE")
        out += Script.parse_string("OP_2DROP")
        out += Script.parse_string("OP_ENDIF")

        # End of termination conditions --------------------------------------------------------------------------------

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
            - stack:    [gradient(P_n, \sum_(i=1)^(n-1) P_i), ..,
                            gradient(P_(n_points_on_stack+1), \sum_(i=1)^(n_points_on_stack) P_i),
                                gradient(P_(n_points_on_stack), \sum_(i=1)^(n_points_on_stack-1) P_i),
                                    P_(n_points_on_stack),
                                        .., gradient(P_3, P_2 + P_1), P_3, gradient(P_2, P_1), P_2, P_1]
            - altstack: [P_n, .., P_(n_points_on_stack+2), P_(n_points_on_stack+1)]

        Stack output:
            - stack:    [P_1 + .. + P_n]
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
            elliptic curve points.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:       [gradient(P_n, \sum_(i=1)^(n-1) P_i), ..,
        #                    gradient(P_(n_points_on_stack+1), \sum_(i=1)^(n_points_on_stack) P_i),
        #                        gradient(P_(n_points_on_stack), \sum_(i=1)^(n_points_on_stack-1) P_i),
        #                            P_(n_points_on_stack),
        #                               .., gradient(P_3, P_2 + P_1), P_3, gradient(P_2, P_1), P_2, P_1]
        # altstack in:   [P_n, .., P_(n_points_on_stack+2), P_(n_points_on_stack+1)]
        # stack out:     [gradient(P_n, \sum_(i=1)^(n-1) P_i), ..,
        #                    gradient(P_(n_points_on_stack+1), \sum_(i=1)^(n_points_on_stack) P_i),
        #                       P_1 + .. + P_(n_points_on_stack)]
        # altstack out:  [P_n, .., P_(n_points_on_stack+2), P_(n_points_on_stack+1)]
        for _ in range(n_points_on_stack - 1):
            out += self.point_addition_with_unknown_points(
                take_modulo=False, positive_modulo=False, check_constant=False, clean_constant=False
            )

        # Handle the case in which the were no points on the stack
        if n_points_on_stack == 0:
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")
            n_points_on_altstack -= 1

        # stack in:      [gradient(P_n, \sum_(i=1)^(n-1) P_i), ..,
        #                    gradient(P_(n_points_on_stack+1), \sum_(i=1)^(n_points_on_stack) P_i),
        #                       P_1 + .. + P_(n_points_on_stack)]
        # altstack in:   [P_n, .., P_(n_points_on_stack+2), P_(n_points_on_stack+1)]
        # stack out:     [P_1 + .. + P_n]
        # altstack out:  []
        for _ in range(n_points_on_altstack):
            out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")
            out += self.point_addition_with_unknown_points(
                take_modulo=False, positive_modulo=False, check_constant=False, clean_constant=False
            )

        if take_modulo:
            # Check if the output is the point at infinity, in that case do nothing
            out += Script.parse_string("OP_2DUP OP_CAT 0x0000 OP_EQUAL OP_NOT OP_IF")
            out += Script.parse_string("OP_TOALTSTACK")
            out += pick(position=-1, n_elements=1)
            out += mod(stack_preparation="", is_positive=positive_modulo)
            out += mod(is_positive=positive_modulo, is_constant_reused=False)
            out += Script.parse_string("OP_ENDIF")

        out += roll(position=-1, n_elements=1) + Script.parse_string("OP_DROP") if clean_constant else Script()

        return out

    def unrolled_multiplication(
        self,
        max_multiplier: int,
        modulo_threshold: int,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
        fixed_length_unlock: bool = False,
    ) -> Script:
        """Unrolled double-and-add scalar multiplication loop in E(F_q).

        Stack input:
            - stack:    [q, ..., marker_a_is_zero, gradient_operations, P := (xP, yP)], `marker_a_is_zero` is `OP_1`
                if a == 0, `gradient_operations` contains the list of gradients and operational steps obtained from the
                self.unrolled_multiplication_input method, `P` is a point on E(F_q)
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
            Script to multiply a point on E(F_q) using double-and-add scalar multiplication.

        Notes:
            The formula for EC point addition `P + Q` where `Q != -P` and `P` and `Q` are not the point at infinity,
            where the curve is in short Weierstrass form, is:
                `x_(P+Q) = lambda^2 - x_P - x_Q`
                `y_(P+Q) = -y_P + (x_(P+Q) - x_P) * lambda`
            where lambda is the gradient of the line through P and Q. Then, we have (with q exchanged for current_size
            in future steps):

            `log_2(abs(x_(P+Q)) <= log_2(q^2 + 2q) = log_2(q) + log_2(q+2) <= 2 log_2(q+2)`
            `log_2(abs(y_(P+Q)) <= log_2(q + (q^2 + 3q) * q) = log_2(q + q^3 + 3q^2) <= log_2(q) + log_2(1 + q^2 + 3q)`

            At every step we check that the next operation doesn't make `log_2(q) + log_2(1 + q^2 + 3q) >
            modulo_threshold`.
        """
        out = verify_bottom_constant(self.modulus) if check_constant else Script()

        # stack in:  [marker_a_is_zero, [lambdas,a], P]
        # stack out: [marker_a_is_zero, [lambdas,a], P, T]
        out += Script.parse_string("OP_2DUP")

        size_q = ceil(log2(self.modulus))
        current_size = size_q

        # Compute aP
        # stack in:  [marker_a_is_zero, [lambdas, a], P, T]
        # stack out: [marker_a_s_zero, P, aP]
        for i in range(int(log2(max_multiplier)) - 1, -1, -1):
            # This is an approximation, but I'm quite sure it works.
            # We always have to take into account both operations
            # because we don't know which ones are going to be executed.
            size_after_operations = 2 * 4 * current_size
            positive_modulo_i = False

            if size_after_operations > modulo_threshold or i == 0:
                take_modulo = True
                current_size = size_q
                positive_modulo_i = positive_modulo and i == 0
            else:
                take_modulo = False
                current_size = size_after_operations

            # Roll marker to decide whether to execute the loop and the auxiliary data
            # stack in:  [auxiliary_data, marker_doubling, P, T]
            # stack out: [auxiliary_data, P, T, marker_doubling]
            out += roll(position=4, n_elements=1)

            # stack in:  [auxiliary_data, P, T, marker_doubling]
            # stack out: [P, T] if marker_doubling = 0, else [P, 2T]
            out += Script.parse_string("OP_IF")  # Check marker for executing iteration
            out += self.point_algebraic_doubling(
                take_modulo=take_modulo,
                check_constant=False,
                clean_constant=False,
                verify_gradient=True,
                positive_modulo=positive_modulo_i,
                gradient=StackFiniteFieldElement(4, False, 1),
                P=StackEllipticCurvePoint(
                    StackFiniteFieldElement(1, False, 1),
                    StackFiniteFieldElement(0, False, 1),
                ),
                rolling_options=boolean_list_to_bitmask([True, True]),
            )  # Compute 2T

            # Roll marker for addition and auxiliary data addition
            # stack in:  [auxiliary_data_addition, marker_addition, P, 2T]
            # stack out: [auxiliary_data_addition, P, 2T, marker_addition]
            out += roll(position=4, n_elements=1)

            # Check marker for +P and compute 2T + P if marker is 1
            # stack in:  [auxiliary_data_addition, P, 2T, marker_addition]
            # stack out: [P, 2T, if marker_addition = 0, else P, (2T+P)]
            out += Script.parse_string("OP_IF")
            out += self.point_algebraic_addition(
                take_modulo=take_modulo,
                check_constant=False,
                clean_constant=False,
                verify_gradient=True,
                positive_modulo=positive_modulo_i,
                gradient=StackFiniteFieldElement(4, False, 1),
                P=StackEllipticCurvePoint(
                    StackFiniteFieldElement(3, False, 1),
                    StackFiniteFieldElement(2, False, 1),
                ),
                Q=StackEllipticCurvePoint(
                    StackFiniteFieldElement(1, False, 1),
                    StackFiniteFieldElement(0, False, 1),
                ),
                rolling_options=boolean_list_to_bitmask([not fixed_length_unlock, False, True]),
            )  # Compute 2T + P

            # Conclude the conditional branches and clear auxiliary data
            if fixed_length_unlock:
                out += (
                    Script.parse_string("OP_ENDIF OP_ELSE")
                    + roll(position=5, n_elements=2)
                    + Script.parse_string("OP_2DROP OP_ENDIF")
                )
                out += roll(position=4, n_elements=1) + Script.parse_string("OP_DROP")
            else:
                out += Script.parse_string("OP_ENDIF OP_ENDIF")

        # Check if a == 0
        # stack in:  [marker_a_is_zero, P, aP]
        # stack out: [P, 0x00, 0x00 if a == 0, else P aP]
        out += roll(position=4, n_elements=1)
        out += Script.parse_string("OP_IF")
        out += Script.parse_string("OP_2DROP 0x00 0x00")
        out += Script.parse_string("OP_ENDIF")

        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")

        return out

    def msm_with_fixed_bases(
        self,
        bases: list[list[int]],
        max_multipliers: list[int],
        modulo_threshold: int,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        positive_modulo: bool = True,
        extractable_scalars: int = 0,
    ) -> Script:
        r"""Multi-scalar multiplication script in E(F_q) with fixed bases.

        This function returns the script that computes a multi-scalar multiplication. That is,
        it computes the operation:
            ((a_1, .., a_n), (P_1, .., P_n)) --> \sum_(i=1)^n a_i P_i
        where the a_i's are the scalars, and the P_i's are the bases. The script hard-codes the bases.

        Stack in:
            - stack:    [gradient[a_1 * P_1, \sum_(i=2)^(n) a_i * P_i], .., gradient[a_n * P_n, a_(n-1) * P_(n-1)],
                            a_n, gradients[a_n, P_n], .., a_2, gradients[a_2, P_2], a_1, gradients[a_1, P_1]]
            - altstack: []

        Stack output:
            - stack:    [a_1 * P_1 + .. + a_n * P_n]
            - altstack: []

        Above, gradients[a_i, P_i] are the gradients required to execute `self.unrolled_multiplication` on input:
            stack: [a_i, gradients[a_i, P_i] P_i]
        While `P_i` are the fixed bases

        Args:
            bases (list[list[int]]): The bases of the multi scalar multiplication, passed as a list of coordinates.
                `bases[i]` is `bases[i] = [x, y]` the list of the coordinates of P_i.
            max_multipliers (list[int]): `max_multipliers[i]` is the maximum value allowed for `a_i`.
            modulo_threshold (int): Bit-length threshold. Values whose bit-length exceeds it are reduced modulo `q`.
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

        # stack in:     [gradient[a_1 * P_1, \sum_(i=2)^(n) a_i * P_i], .., gradient[a_n * P_n, a_(n-1) * P_(n-1)],
        #                   a_n, gradients[a_n, P_n], .., a_2, gradients[a_2, P_2], a_1, gradients[a_1, P_1]]
        # stack out:    [gradient[a_1 * P_1, \sum_(i=2)^(n) a_i * P_i], .., gradient[a_n * P_n, a_(n-1) * P_(n-1)]]
        # altstack out: [a_1 * P_1, .., a_n * P_n]
        for i, (base, multiplier) in enumerate(zip(bases, max_multipliers)):
            assert len(base) != 0
            # Load `base` to the stack
            out += nums_to_script(base)
            # Compute a_i * P_i
            out += self.unrolled_multiplication(
                max_multiplier=multiplier,
                modulo_threshold=modulo_threshold,
                check_constant=False,
                clean_constant=False,
                positive_modulo=False,
                fixed_length_unlock=(i < extractable_scalars),
            )
            # Put a_i * P_i on the altstack
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")
            # Drop P_i
            out += Script.parse_string("OP_2DROP")

        # stack in:     [gradient[a_1 * P_1, \sum_(i=2)^(n) a_i * P_i], .., gradient[a_n * P_n, a_(n-1) * P_(n-1)],
        #                   a_n * P_n]
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

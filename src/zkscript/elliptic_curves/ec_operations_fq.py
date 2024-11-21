"""Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q)."""

from tx_engine import Script

from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import bitmask_to_boolean_list, bool_to_moving_function, check_order
from src.zkscript.util.utility_scripts import mod, move, nums_to_script, pick, roll, verify_bottom_constant


class EllipticCurveFq:
    """Construct Bitcoin scripts that perform arithmetic operations over the elliptic curve E(F_q).

    Attributes:
        MODULUS: The characteristic of the field F_q.
        CURVE_A: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
    """

    def __init__(self, q: int, curve_a: int):
        """Initialise the elliptic curve group E(F_q).

        Args:
            q: The characteristic of the field F_q.
            curve_a: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q).
        """
        self.MODULUS = q
        self.CURVE_A = curve_a

    def point_algebraic_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        positive_modulo: bool = True,
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
            - stack    = [q, .., gradient, .., P, .., Q, ..]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., {gradient}, .., {P}, .., {Q}, .., (P_+ Q_)]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
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
                - `stack_elements` is not None, but it does not contain all the keys `gradient`, `P`, `Q`

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` != `Q_` and `P_ != -Q_` and `P_`, `Q_` not the point at infinity
        """
        check_order([gradient, P, Q])
        return (
            self.__point_algebraic_addition_verifying_gradient(
                take_modulo, check_constant, clean_constant, positive_modulo, gradient, P, Q, rolling_options
            )
            if verify_gradient
            else self.__point_algebraic_addition_without_verifying_gradient(
                take_modulo, check_constant, clean_constant, positive_modulo, gradient, P, Q, rolling_options
            )
        )

    def point_algebraic_doubling(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        positive_modulo: bool = True,
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
            - stack    = [{q}, .., {gradient}, .., {P}, .., 2P_]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
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
                take_modulo, check_constant, clean_constant, positive_modulo, gradient, P, rolling_options
            )
            if verify_gradient
            else self.__point_algebraic_doubling_without_verifying_gradient(
                take_modulo, check_constant, clean_constant, positive_modulo, gradient, P, rolling_options
            )
        )

    def __point_algebraic_addition_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        positive_modulo: bool = True,
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
            - stack    = [{q}, .., {gradient}, .., {P}, .., {Q}, .., (P_+ Q_)]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
<<<<<<< Updated upstream
=======
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
>>>>>>> Stashed changes
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

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

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
        verify_gradient += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
        verify_gradient += mod(stack_preparation="")
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
            - stack    = [{q}, .., {gradient}, .., {P}, .., {Q}, .., (P_+ Q_)]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
<<<<<<< Updated upstream
=======
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
>>>>>>> Stashed changes
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

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

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
            y_coordinate += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
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
            - stack    = [{q}, .., {gradient}, .., {P}, .., 2P_]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
<<<<<<< Updated upstream
=======
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
>>>>>>> Stashed changes
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

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        curve_a = self.CURVE_A

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
        verify_gradient += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
        verify_gradient += mod(stack_preparation="")
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
<<<<<<< Updated upstream
=======
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
>>>>>>> Stashed changes
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

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

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
            y_coordinate += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
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
            - stack    = [q, .., gradient P Q]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., (P + Q)]
            - altstack = []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
<<<<<<< Updated upstream
=======
            positive_modulo (bool): If `True` the modulo of the result is taken positive. Defaults to `True`.
>>>>>>> Stashed changes
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            A Bitcoin script that compute the sum of `P` and `Q`, handling all possibilities.

        Preconditions:
            - P and Q are points on F_q
            - If P != -Q, then gradient is the gradient of the line through P and Q
            - If P = -Q or P is the point at infinity, or Q is the point at infinity, then do not put gradient

        Notes:
            If P = -Q, then we return 0x00 0x00, i.e., we encode the point at infinity as (0x00,0x00) (notice that
            these are data payloads, they are not numbers - points are assumed to be passed as numbers, which means that
            (0,0) would have to be passed as OP_0 OP_0)
        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        curve_a = self.CURVE_A

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
        out += Script.parse_string("OP_DEPTH OP_1SUB OP_PICK OP_MOD OP_0 OP_NUMNOTEQUAL")
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

        # After this, the stack is: (P+Q) q, altstack = [Verify(gradient)]
        out += compute_x_coordinate + compute_y_coordinate + pick(position=-1, n_elements=1)

        # If needed, mod out
        # After this, the stack is: (P+Q) q, altstack = [Verify(gradient)] with the coefficients in Fq (if executed)
        if take_modulo:
            batched_modulo = mod(stack_preparation="", is_positive=positive_modulo)  # Mod y
            batched_modulo += mod(stack_preparation="OP_TOALTSTACK", is_positive=positive_modulo)  # Mod x
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            out += batched_modulo

        check_gradient = Script.parse_string("OP_FROMALTSTACK")
        check_gradient += mod(stack_preparation="", is_mod_on_top=False, is_constant_reused=False, is_positive=True)
        check_gradient += Script.parse_string("OP_0 OP_EQUALVERIFY")

        # Check gradient was correct
        out += check_gradient

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

        if clean_constant:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")

        return out

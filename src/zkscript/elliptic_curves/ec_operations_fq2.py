"""ec_operations_fq2 module.

This module enables constructing Bitcoin scripts that perform elliptic curve arithmetic in E(F_q^2).
"""

from tx_engine import Script

from src.zkscript.types.stack_elements import StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import bitmask_to_boolean_list, bool_to_moving_function, check_order
from src.zkscript.util.utility_scripts import mod, move, nums_to_script, pick, roll, verify_bottom_constant


class EllipticCurveFq2:
    """Construct Bitcoin scripts that perform elliptic curve arithmetic in E(F_q^2).

    Attributes:
        MODULUS: The characteristic of the field F_q.
        CURVE_A: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q^2).
        FQ2: The script implementation of the field F_q^2.
    """

    def __init__(self, q: int, curve_a: list[int], fq2):
        """Initialise the elliptic curve group E(F_q^2).

        Args:
            q: The characteristic of the field F_q.
            curve_a: The `a` coefficient in the Short-Weierstrass equation of the curve (an element in F_q^2).
            fq2: The script implementation for the field F_q^2.
        """
        self.MODULUS = q
        self.CURVE_A = curve_a
        self.FQ2 = fq2

    def point_algebraic_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(9, False, 2),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(7, False, 2),  # noqa: B008
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq2.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        The function branches according to the value of verify_gradient.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, .., Q, ..]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., {gradient}, .., {P}, .., {Q}, .., (P_+ Q_)]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P if P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            gradient (StackFiniteFieldElement): The position of gradient through P_ and Q_ in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackFiniteFieldElement(9, False, 2)
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(7, False, 2),StackFiniteFieldElement(5, False, 2)
                    )
            Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(3, False, 2),StackFiniteFieldElement(1, False, 2)
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
        return (
            self.point_algebraic_addition_verifying_gradient(
                take_modulo, check_constant, clean_constant, gradient, P, Q, rolling_options
            )
            if verify_gradient
            else self.point_algebraic_addition_without_verifying_gradient(
                take_modulo, check_constant, clean_constant, gradient, P, Q, rolling_options
            )
        )

    def point_algebraic_doubling(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(5, False, 2),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_options: int = 3,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq2.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        The function branches according to the value of verify_gradient.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., {gradient}, .., {P}, .., 2P_]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P if P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            gradient (StackFiniteFieldElement): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackFiniteFieldElement(5,False,2).
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackEllipticCurvePoint(
                        StackFiniteFieldElement(3,False,2),StackFiniteFieldElement(1,False,2)
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
        return (
            self.point_algebraic_doubling_verifying_gradient(
                take_modulo, check_constant, clean_constant, gradient, P, rolling_options
            )
            if verify_gradient
            else self.point_algebraic_doubling_without_verifying_gradient(
                take_modulo, check_constant, clean_constant, gradient, P, rolling_options
            )
        )

    def point_negation(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Perform point negation on an elliptic curve defined over Fq2.

        Stack input:
            - stack:    [q, ..., P]
            - altstack: []

        Stack output:
            - stack:    [q, ..., -P]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            is_constant_reused (bool | None, optional): If `True`, at the end of the execution, q is left as the ???
                element at the top of the stack.

        Returns:
            Script to negate a point on E(F_q^2).

        Note:
            The constant cannot be cleaned from inside this function.
        """
        assert (not clean_constant) or (
            clean_constant is None
        ), "It is not possible to clean the constant from inside this function"
        # Fq2 implementation
        fq2 = self.FQ2

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Check if P is point at infinity
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += Script.parse_string("OP_CAT OP_CAT OP_CAT 0x00000000 OP_EQUAL OP_NOT OP_IF")

        # If not, carry out the negation
        out += fq2.negate(take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False)

        if take_modulo:
            assert is_constant_reused is not None
            # After this, the stack is: P.x0, altstack = [-P.y, P.x1]
            out += Script.parse_string(" ".join(["OP_TOALTSTACK"] * 3))

            fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            batched_modulo = mod(stack_preparation="")
            batched_modulo += mod()
            batched_modulo += mod()
            batched_modulo += mod(is_constant_reused=is_constant_reused)

            out += fetch_q + batched_modulo

        # Else, exit
        out += Script.parse_string("OP_ENDIF")

        return out

    def point_algebraic_addition_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(9, False, 2),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(7, False, 2),  # noqa: B008
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq2.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [Q, .., gradient, .., P, .., Q, ..]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., {gradient}, .., {P}, .., {Q}, .., (P_+ Q_)]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P if P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            gradient (StackFiniteFieldElement): The position of gradient through P_ and Q_ in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackFiniteFieldElement(9, False, 2)
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(7, False, 2),StackFiniteFieldElement(5, False, 2)
                    )
            Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(3, False, 2),StackFiniteFieldElement(1, False, 2)
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
        check_order([gradient, P, Q])
        is_gradient_rolled, is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Fq2 implementation
        fq2 = self.FQ2

        # Write:
        #   P_ = -P if P.y.negate else P
        #   Q_ = -Q if Q.y.negate else Q

        # Verify that gradient is the gradient between P_ and Q_
        # stack in:  [q, .., gradient, .., P, .., Q, ..]
        # stack out: [q, .., gradient, .., P, .., Q, .., gradient, xP, gradient, xP]
        verify_gradient = move(gradient, bool_to_moving_function(is_gradient_rolled))  # Move gradient
        verify_gradient += move(P.x.shift(2), bool_to_moving_function(is_p_rolled))  # Move xP
        verify_gradient += pick(position=3, n_elements=4)  # Duplicate gradient and xP
        # stack in:  [q, .., gradient, .., P, .., Q, .., gradient, xP, gradient, xP]
        # stack out: [q, .., gradient, .., P, .., Q, .., gradient, xP, xQ, [gradient * (xP - xQ)]]
        verify_gradient += move(Q.x.shift(8), bool_to_moving_function(is_q_rolled))  # Move xQ
        verify_gradient += Script.parse_string("OP_2SWAP OP_2OVER")  # Swap xP and xQ, duplicate xQ
        verify_gradient += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute xP - xQ
        verify_gradient += roll(position=5, n_elements=2)  # Bring gradient on top of the stack
        verify_gradient += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute gradient * (x_P - x_Q)
        # stack in:  [q, .., gradient, .., P, .., Q, .., gradient, xP, xQ, [gradient * (xP - xQ)]]
        # stack out: [q, .., gradient, .., P, .., Q, .., gradient, xP, xQ,
        #               [gradient * (xP - xQ)] (yP_)_1 [(yQ_)_1 - (yP_)_1]]
        verify_gradient += move(
            Q.y.shift(8), bool_to_moving_function(is_q_rolled), start_index=1, end_index=2
        )  # Move (yQ)_1
        verify_gradient += Script.parse_string("OP_NEGATE") if Q.negate else Script()
        verify_gradient += move(
            P.y.shift(9 - 3 * is_q_rolled), bool_to_moving_function(is_p_rolled), start_index=1, end_index=2
        )  # Move (yP)_1
        verify_gradient += Script.parse_string("OP_NEGATE") if P.negate else Script()
        verify_gradient += Script.parse_string("OP_TUCK OP_SUB")  # Duplicate (yP_)_1 and compute (yQ_)_1 - (yP_)_1
        # stack in:  [q, .., gradient, .., P, .., Q, .., gradient, xP, xQ,
        #               [gradient * (xP - xQ)] (yP_)_1 [(yQ_)_1 - (yP_)_1]]
        # stack out: [q, .., gradient, .., P, .., Q, .., gradient, xP, xQ, (yP_)_1 (yP_)_0, or fail]
        verify_gradient += move(
            Q.y.shift(10 - 1 * is_q_rolled), bool_to_moving_function(is_q_rolled), start_index=0, end_index=1
        )  # Move (yQ)_0
        verify_gradient += Script.parse_string("OP_NEGATE") if Q.negate else Script()
        verify_gradient += move(
            P.y.shift(11 - 4 * is_q_rolled - 1 * is_p_rolled),
            bool_to_moving_function(is_p_rolled),
            start_index=0,
            end_index=1,
        )  # Move (yP)_0
        verify_gradient += Script.parse_string("OP_NEGATE") if P.negate else Script()
        verify_gradient += Script.parse_string("OP_TUCK OP_SUB")  # Duplicate (yP_)_0 and compute (yQ_)_0 - (yP_)_0
        verify_gradient += roll(position=2, n_elements=1)  # Bring [(yQ_)_1 - (yP_)_1] on top
        verify_gradient += roll(position=5, n_elements=2)  # Bring [gradient * (xP - xQ)] on top
        verify_gradient += fq2.add(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute gradient * (x_P - x_Q) + (yQ_ - yP_)
        verify_gradient += Script.parse_string("OP_CAT OP_0 OP_EQUALVERIFY")

        # Compute x-coordinate of P_ + Q_
        # stack in:     [q, .., gradient, .., P, .., Q, .., gradient, xP, xQ, (yP_)_1, (yP_)_0]
        # altstack in:  []
        # stack out:    [q, .., gradient, .., P, .., Q, .., xP, gradient, x(P_ + Q_)]
        # altstack out: [(yP_)_0, (yP_)_1]
        x_coordinate = Script.parse_string(" ".join(["OP_TOALTSTACK"] * 2))  # Put (yP_)_0, (yP_)_1 on the altstack
        x_coordinate += pick(position=3, n_elements=2)  # Duplicate xP
        x_coordinate += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)  # Compute (xP + xQ)
        x_coordinate += Script.parse_string("OP_2ROT OP_2SWAP OP_2OVER")  # Roll gradient, reorder, duplicate gradient
        x_coordinate += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute gradient^2
        x_coordinate += Script.parse_string("OP_2SWAP")  # Swap gradient^2 and (xP + xQ)
        x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute gradient^2 - (xP + xQ)

        # Compute y-coordinate of P_ + Q_
        # stack in:     [q, .., gradient, .., P, .., Q, .., xP, gradient, x(P_ + Q_)]
        # altstack in:  [(yP_)_0, (yP_)_1]
        # stack out:    [q, .., gradient, .., P, .., Q, .., x(P_ + Q_), y(P_ + Q_)]
        # altstack out: []
        y_coordinate = Script.parse_string("OP_2ROT OP_2OVER")  # Rotate xP, duplicate x(P_ + Q_)
        y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=5, n_elements=2)  # Bring gradient on top
        y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute gradient * (xP - x(P_+Q_))
        y_coordinate += Script.parse_string(
            "OP_FROMALTSTACK OP_SUB"
        )  # Compute [gradient * (xP - x(P_+Q_))]_1 - (yP_)_1
        if take_modulo:
            y_coordinate += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            y_coordinate += mod(stack_preparation="")  # Compute {[gradient * (xP - x(P_+Q_))]_1 - (yP_)_1} % q
            y_coordinate += roll(position=2, n_elements=1)  # Bring [gradient * (xP - x(P_+Q_))]_0 on top
            y_coordinate += Script.parse_string(
                "OP_FROMALTSTACK OP_SUB"
            )  # Compute [gradient * (xP - x(P_+Q_))]_0 - (yP_)_0
            y_coordinate += roll(position=2, n_elements=1) + mod(
                stack_preparation="", is_constant_reused=False
            )  # Compute {[gradient * (xP - x(P_+Q_))]_0 - (yP_)_0} % q
        else:
            y_coordinate += roll(position=1, n_elements=1)  # Bring gradient * (xP - x(P_+Q_))]_0 on top
            y_coordinate += Script.parse_string(
                "OP_FROMALTSTACK OP_SUB"
            )  # Compute [gradient * (xP - x(P_+Q_))]_0 - (yP_)_0
        y_coordinate += roll(
            position=1, n_elements=1
        )  # Swap {[gradient * (xP - x(P_+Q_))]_0 - (yP_)_0} and {[gradient * (xP - x(P_+Q_))]_1 - (yP_)_1}

        out += verify_gradient + x_coordinate + y_coordinate
        return out

    def point_algebraic_addition_without_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(9, False, 2),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(7, False, 2),  # noqa: B008
            StackFiniteFieldElement(5, False, 2),  # noqa: B008
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq2.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q` without
        verifying the gradient provided.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, .., Q, ..]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., {gradient}, .., {P}, .., {Q}, .., (P_+ Q_)]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P if P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            gradient (StackFiniteFieldElement): The position of gradient through P_ and Q_ in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackFiniteFieldElement(9, False, 2)
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(7, False, 2),StackFiniteFieldElement(5, False, 2)
                    )
            Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                its length, whether it should be negated, and whether it should be rolled or picked.
                Defaults to: StackEllipticCurvePoint(
                    StackFiniteFieldElement(3, False, 2),StackFiniteFieldElement(1, False, 2)
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
            This function does not check the validity of the gradient provided.
        """
        check_order([gradient, P, Q])
        is_gradient_rolled, is_p_rolled, is_q_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Fq2 implementation
        fq2 = self.FQ2

        # Write:
        #   P_ = -P if P.y.negate else P
        #   Q_ = -Q if Q.y.negate else Q

        # Compute x-coordinate of P_ + Q_
        # stack in:  [q, .., gradient, .., P, .., Q, ..]
        # stack out: [q, .., gradient, .., P, .., Q, .., gradient, xP, x(P_+Q_)]
        x_coordinate = move(gradient, bool_to_moving_function(is_gradient_rolled))  # Move gradient
        x_coordinate += pick(position=1, n_elements=2)  # Duplicate gradient
        x_coordinate += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute gradient^2
        x_coordinate += move(P.x.shift(4), bool_to_moving_function(is_p_rolled))  # Move xP
        x_coordinate += move(Q.x.shift(6), bool_to_moving_function(is_q_rolled))  # Move xQ
        x_coordinate += pick(position=3, n_elements=2)  # Duplicate xP
        x_coordinate += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)  # Compute (xP + xQ)
        x_coordinate += roll(position=5, n_elements=2)  # Bring gradient^2 on top
        x_coordinate += roll(position=3, n_elements=2)  # Bring (xP + xQ) on top
        x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute gradient^2 - (xP + xQ)

        # Compute y-coordinate of P_ + Q_
        # stack in:  [q, .., gradient, .., P, .., Q, .., gradient, xP, x(P_ + Q_)]
        # stack out: [q, .., gradient, .., P, .., Q, .., x(P_ + Q_), y(P_ + Q_)]
        y_coordinate = Script.parse_string("OP_2SWAP OP_2OVER")  # Rotate xP, duplicate x(P_ + Q_)
        y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=5, n_elements=2)  # Bring gradient on top
        y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute gradient * (xP - x(P_+Q_))
        y_coordinate += Script.parse_string("OP_TOALTSTACK")
        y_coordinate += move(
            P.y.shift(3 - 2 * is_q_rolled), bool_to_moving_function(is_p_rolled), start_index=0, end_index=1
        )  # Move yP_0
        y_coordinate += Script.parse_string("OP_ADD" if P.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            y_coordinate += mod(stack_preparation="")
        y_coordinate += Script.parse_string("OP_FROMALTSTACK")
        y_coordinate += move(
            P.y.shift(4 - 2 * is_q_rolled + 1 * take_modulo),
            bool_to_moving_function(is_p_rolled),
            start_index=1,
            end_index=2,
        )  # Move yP_1
        y_coordinate += Script.parse_string("OP_ADD" if P.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += roll(position=2, n_elements=1) + mod(stack_preparation="", is_constant_reused=False)

        drop_yq = move(Q.y.shift(4), bool_to_moving_function(is_q_rolled))  # Move yQ
        drop_yq += Script.parse_string("OP_2DROP")

        out += x_coordinate + y_coordinate
        if is_q_rolled:
            out += drop_yq  # Drop yQ
        if clean_constant and not take_modulo:
            out += roll(position=-1, n_elements=1) + Script.parse_string("OP_DROP")

        return out

    def point_algebraic_doubling_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(5, False, 2),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_options: int = 3,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq2.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., {gradient}, .., {P}, .., 2P_]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P if P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            gradient (StackFiniteFieldElement): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackFiniteFieldElement(5,False,2).
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackEllipticCurvePoint(
                        StackFiniteFieldElement(3,False,2),StackFiniteFieldElement(1,False,2)
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
        is_gradient_rolled, is_p_rolled = bitmask_to_boolean_list(rolling_options, 2)

        # Fq2 implementation
        fq2 = self.FQ2
        # A coefficient
        curve_a = self.CURVE_A

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Write:
        #   P_ = -P if P.y.negate else P

        # Verify that gradient is the gradient of the line tangent at P_
        # stack in:  [q, .., gradient, .., P, ..]
        # stack out: [q, .., gradient, .., P, .., gradient, yP, gradient, yP]
        verify_gradient = move(gradient, bool_to_moving_function(is_gradient_rolled))  # Move gradient
        verify_gradient += move(P.y.shift(2), bool_to_moving_function(is_p_rolled))  # Move yP
        verify_gradient += pick(position=3, n_elements=4)  # Duplicate gradient and xP
        # stack in:  [q, .., gradient, .., P, .., gradient, yP, gradient, yP]
        # stack out: [q, .., gradient, .., P, .., gradient, yP, (2*gradient*yP_)]
        verify_gradient += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute lamdba * yP
        verify_gradient += Script.parse_string("OP_2")
        verify_gradient += Script.parse_string("OP_NEGATE") if P.negate else Script()
        verify_gradient += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        # stack in:  [q, .., gradient, .., P, .., gradient, yP, (2*gradient*yP_)]
        # stack out: [q, .., gradient, .., P, .., gradient, yP, xP, or fail]
        verify_gradient += move(P.x.shift(6 - 2 * is_p_rolled), bool_to_moving_function(is_p_rolled))  # Move xP
        verify_gradient += roll(position=3, n_elements=2)  # Bring (2*gradient*yP_) on top
        verify_gradient += pick(position=3, n_elements=2)  # Duplicate xP
        verify_gradient += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute xP^2
        verify_gradient += Script.parse_string("OP_3 OP_TUCK")
        verify_gradient += Script.parse_string("OP_MUL")  # Compute 3 * (xP^2)_1
        if curve_a[1]:
            verify_gradient += nums_to_script([curve_a[1]])
            verify_gradient += Script.parse_string("OP_ADD")  # Compute 3 * (xP^2)_1 + a_1
        verify_gradient += Script.parse_string("OP_TOALTSTACK")
        verify_gradient += Script.parse_string("OP_MUL")  # Compute 3 * (xP^2)_0
        if curve_a[0]:
            verify_gradient += nums_to_script([curve_a[0]])
            verify_gradient += Script.parse_string("OP_ADD")  # Compute 3 * (xP^2)_1 + a_1
        verify_gradient += Script.parse_string("OP_FROMALTSTACK")
        verify_gradient += fq2.subtract(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute 2*gradient*yP_ - (3xP^2 + a)
        verify_gradient += Script.parse_string("OP_CAT OP_0 OP_EQUALVERIFY")

        # Compute x-coordinate of 2P_
        # stack in:  [q, .., gradient, .., P, .., gradient, yP, xP]
        # stack out: [q, .., gradient, .., P, .., yP, gradient, xP, x(2P_)]
        x_coordinate = roll(position=5, n_elements=2)  # Bring gradient on top
        x_coordinate += pick(position=1, n_elements=2)  # Duplicate gradient
        x_coordinate += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute gradient^2
        x_coordinate += roll(position=5, n_elements=2)  # Bring xP on top
        x_coordinate += roll(position=3, n_elements=2)  # Bring gradient on top
        x_coordinate += pick(position=3, n_elements=2)  # Duplicate xP
        x_coordinate += Script.parse_string("OP_2")
        x_coordinate += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute 2 * xP
        x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute gradient^2 - 2*xP

        # Compute y-coordinate of 2P_
        # stack in:  [q, .., gradient, .., P, .., yP, gradient, xP, x(2P_)]
        # stack out: [q, .., gradient, .., P, .., x(2P_) y(2P_)]
        y_coordinate = roll(position=3, n_elements=2)  # Bring xP on top
        y_coordinate += pick(position=3, n_elements=2)  # Duplicate x(2P_) on top
        y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_(2P_)
        y_coordinate += roll(position=5, n_elements=2)  # Bring gradient on top
        y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute gradient * (xP - x_(2P))
        y_coordinate += roll(position=5, n_elements=2)  # Bring yP on top
        y_coordinate += (
            fq2.add(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )
            if P.y.negate
            else fq2.subtract(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )
        )  # Compute y_(2P)

        out += verify_gradient + x_coordinate + y_coordinate
        return out

    def point_algebraic_doubling_without_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(5, False, 2),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 2),  # noqa: B008
            StackFiniteFieldElement(1, False, 2),  # noqa: B008
        ),
        rolling_options: int = 3,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq2.

        This function computes the algebraic doubling of P for the elliptic curve point `P` without
        verifying the gradient provided.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
            - stack    = [q, .., gradient, .., P, ..]
            - altstack = []

        Stack output:
            - stack    = [{q}, .., {gradient}, .., {P}, .., 2P_]
            - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P if P.y.negate else P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            gradient (StackFiniteFieldElement): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackFiniteFieldElement(5,False,2).
            P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked.
                    Defaults to: StackEllipticCurvePoint(
                        StackFiniteFieldElement(3,False,2),StackFiniteFieldElement(1,False,2)
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

        Notes:
            This function does not check the validity of the gradient provided.
        """
        check_order([gradient, P])
        is_gradient_rolled, is_p_rolled = bitmask_to_boolean_list(rolling_options, 2)

        # Fq2 implementation
        fq2 = self.FQ2

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Write:
        #   P_ = -P if P.y.negate else P

        # Compute x-coordinate of 2P_
        # stack in:  [q, .., gradient, .., P, ..]
        # stack out: [q, .., gradient, .., P, .., gradient, xP, x(2P_)]
        x_coordinate = move(gradient, bool_to_moving_function(is_gradient_rolled))  # Move gradient
        x_coordinate += pick(position=1, n_elements=2)  # Duplicate gradient
        x_coordinate += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute gradient^2
        x_coordinate += move(P.x.shift(4), bool_to_moving_function(is_p_rolled))  # Bring xP on top
        x_coordinate += pick(position=1, n_elements=2)  # Duplicate xP
        x_coordinate += Script.parse_string("OP_2")
        x_coordinate += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute 2 * xP
        x_coordinate += roll(position=5, n_elements=2)  # Bring gradient^2 on top
        x_coordinate += roll(position=3, n_elements=2)  # Swap 2xP and gradient^2
        x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute gradient^2 - 2*xP

        # Compute y-coordinate of 2P_
        # stack in:  [q, .., gradient, .., P, .., gradient, xP, x(2P_)]
        # stack out: [q, .., gradient, .., P, .., x(2P_), y(2P_)]
        y_coordinate = roll(position=3, n_elements=2)  # Bring xP on top
        y_coordinate += pick(position=3, n_elements=2)  # Duplicate x(2P_)
        y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_(2P_)
        y_coordinate += roll(position=5, n_elements=2)  # Bring gradient on top
        y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute gradient * (xP - x_(2P))
        y_coordinate += move(P.y.shift(4), bool_to_moving_function(is_p_rolled))  # Bring yP on top
        y_coordinate += (
            fq2.add(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )
            if P.negate
            else fq2.subtract(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )
        )  # Compute y_(2P)

        out += x_coordinate + y_coordinate

        return out

from tx_engine import Script

from src.zkscript.util.utility_classes import StackElements, StackEllipticCurvePoint, StackNumber
from src.zkscript.util.utility_scripts import nums_to_script, pick, roll, verify_bottom_constant, mod


class EllipticCurveFq2:
    """Elliptic curve arithmetic over Fq2."""

    def __init__(self, q: int, curve_a: list[int], fq2):
        # Characteristic of the field over which the curve is defined
        self.MODULUS = q
        # A coefficient of the curve over which we carry out the operations, as a list of integers
        self.CURVE_A = curve_a
        # Fq2 implementation in script
        self.FQ2 = fq2

    def point_algebraic_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq2.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        The function branches according to the value of verify_gradient.
        If `take_modulo` is set to `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P .. Q ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. {Q} .. (P_+ Q_)]
        - altstack = []

        where {-} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = P if not P.y.negate else -P
        Q_ = Q if not Q.y.negate else -Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None, optional): If `True`, check if the constant (q) is valid before proceeding.
            clean_constant (bool | None, optional): If `True`, clean the constant by removing it
                from the stack after use.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            stack_elements (StackElements | None, optional): Dictionary with keys:
                - lambda (StackNumber): The position of gradient through P_ and Q_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                If None, the default dictionary is:
                    stack_elements = {
                        "lambda" : StackNumber(9,2,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(7,2,False,roll),StackNumber(5,2,False,roll)),
                        "Q" : StackEllipticCurvePoint(StackNumber(3,2,False,roll),StackNumber(1,2,False,roll)),
                    }

        Returns:
            A Bitcoin Script that computes P_ + Q_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `lambda` comes after `P` in the stack
                - `P` comes after `Q` in the stack
                - `stack_elements` is not None, but it does not contain all the keys `lambda`, `P`, `Q`

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` != `Q_` and `P_ != -Q_` and `P_`, `Q_` not the point at infinity

        Notes:
            This function assumes the input points are represented as minimally encoded, little-endian integers.

        """
        return (
            self.point_algebraic_addition_verifying_gradient(
                take_modulo, check_constant, clean_constant, stack_elements
            )
            if verify_gradient
            else self.point_algebraic_addition_without_verifying_gradient(
                take_modulo, check_constant, clean_constant, stack_elements
            )
        )

    def point_algebraic_doubling(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq2.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        The function branches according to the value of verify_gradient.
        If `take_modulo` is set to `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. 2P_]
        - altstack = []

        where {-} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = P if not P.y.negate else -P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None, optional): If `True`, check if the constant (q) is valid before proceeding.
            clean_constant (bool | None, optional): If `True`, clean the constant by removing it
                from the stack after use.
            verify_gradient (bool): If `True`, the validity of the gradient provided is checked.
            stack_elements (StackElements | None, optional): Dictionary with keys:
                - lambda (StackNumber): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                If None, the default dictionary is:
                    stack_elements = {
                        "lambda" : StackNumber(5,2,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(3,2,False,roll),StackNumber(1,2,False,roll)),
                    }

        Returns:
            A Bitcoin Script that computes 2P_ for the given elliptic curve points `P`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `lambda` comes after `P` in the stack
                - `stack_elements` is not None, but it does not contain all the keys `lambda`, `P`

        Preconditions:
            - The input point `P` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P` not the point at infinity

        Notes:
            This function assumes the input points are represented as minimally encoded, little-endian integers.

        """
        return (
            self.point_algebraic_doubling_verifying_gradient(
                take_modulo, check_constant, clean_constant, stack_elements
            )
            if verify_gradient
            else self.point_algebraic_doubling_without_verifying_gradient(
                take_modulo, check_constant, clean_constant, stack_elements
            )
        )

    def point_negation(
        self,
        take_modulo: bool,
        check_constant: bool | None = None,
        clean_constant: bool | None = None,
        is_constant_reused: bool | None = None,
    ) -> Script:
        """Point negation.

        Input Parameters:
            - Stack: q .. <lambda> P
            - Altstack: []
        Output:
            - -P
        Assumption on parameters:
            - P is a point on E(F_q^2), passed as an element in Fq2
        If take_modulo = True, the coordinates of -P are in F_q

        NOTE: The constant cannot be cleaned from inside this function
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
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq2.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        If `take_modulo` is set to `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P .. Q ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. {Q} .. (P_+ Q_)]
        - altstack = []

        where {-} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = P if not P.y.negate else -P
        Q_ = Q if not Q.y.negate else -Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None, optional): If `True`, check if the constant (q) is valid before proceeding.
            clean_constant (bool | None, optional): If `True`, clean the constant by removing it
                from the stack after use.
            stack_elements (StackElements | None, optional): Dictionary with keys:
                - lambda (StackNumber): The position of gradient through P_ and Q_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                If None, the default dictionary is:
                    stack_elements = {
                        "lambda" : StackNumber(9,2,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(7,2,False,roll),StackNumber(5,2,False,roll)),
                        "Q" : StackEllipticCurvePoint(StackNumber(3,2,False,roll),StackNumber(1,2,False,roll)),
                    }

        Returns:
            A Bitcoin Script that computes P_ + Q_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `lambda` comes after `P` in the stack
                - `P` comes after `Q` in the stack
                - `stack_elements` is not None, but it does not contain all the keys `lambda`, `P`, `Q`

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` != `Q_` and `P_ != -Q_` and `P_`, `Q_` not the point at infinity

        Notes:
            This function assumes the input points are represented as minimally encoded, little-endian integers.
            If this function is used when `P_` != `Q_` or `P_ != -Q_`, then any lambda will pass
            the gradient verification, but the point computed is not going to be `P_ + Q_`.

        """
        stack_elements = (
            {
                "lambda": StackNumber(9, 2, False, roll),
                "P": StackEllipticCurvePoint(StackNumber(7, 2, False, roll), StackNumber(5, 2, False, roll)),
                "Q": StackEllipticCurvePoint(StackNumber(3, 2, False, roll), StackNumber(1, 2, False, roll)),
            }
            if stack_elements is None
            else stack_elements
        )
        if "lambda" not in stack_elements or "P" not in stack_elements or "Q" not in stack_elements:
            msg = f"The stack_elements dictionary must have the following keys:\
                'lambda', 'P', 'Q': stack_elements.keys: { stack_elements.keys()}"
            raise ValueError(msg)
        if not stack_elements["lambda"] < stack_elements["P"]:
            msg = "P must come after lambda in the stack"
            raise ValueError(msg)
        if not stack_elements["P"] < stack_elements["Q"]:
            msg = "Q must come after P in the stack"
            raise ValueError(msg)
        is_q_rolled = stack_elements["Q"].x.move == roll
        is_p_rolled = stack_elements["P"].x.move == roll

        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Fq2 implementation
        fq2 = self.FQ2

        # Write:
        #   P_ = P if not P.y.negate else -P
        #   Q_ = Q if not Q.y.negate else -Q

        # Verify that lambda is the gradient between P_ and Q_
        # Stack in: q .. lambda .. P .. Q ..
        # Stack out: q .. lambda .. P .. Q .. lambda xP lambda xP
        verify_gradient = stack_elements["lambda"].move(
            position=stack_elements["lambda"].position, n_elements=2
        )  # Move lambda
        verify_gradient += stack_elements["P"].x.move(
            position=stack_elements["P"].x.position + 2, n_elements=2
        )  # Move xP
        verify_gradient += pick(position=3, n_elements=4)  # Duplicate lambda and xP
        # Stack in: q .. lambda .. P .. Q .. lambda xP lambda xP
        # Stack out: q .. lambda .. P .. Q .. lambda xP xQ [lambda * (xP - xQ)]
        verify_gradient += stack_elements["Q"].x.move(
            position=stack_elements["Q"].x.position + 8, n_elements=2
        )  # Move xQ
        verify_gradient += Script.parse_string("OP_2SWAP OP_2OVER")  # Swap xP and xQ, duplicate xQ
        verify_gradient += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute xP - xQ
        verify_gradient += roll(position=5, n_elements=2)  # Bring lambda on top of the stack
        verify_gradient += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda * (x_P - x_Q)
        # Stack in: q .. lambda .. P .. Q .. lambda xP xQ [lambda * (xP - xQ)]
        # Stack out: q .. lambda .. P .. Q .. lambda xP xQ [lambda * (xP - xQ)] (yP_)_1 [(yQ_)_1 - (yP_)_1]
        verify_gradient += stack_elements["Q"].y.move(
            position=stack_elements["Q"].y.position + 8 - 1, n_elements=1
        )  # Move (yQ)_1
        verify_gradient += Script.parse_string("OP_NEGATE") if stack_elements["Q"].y.negate else Script()
        verify_gradient += stack_elements["P"].y.move(
            position=stack_elements["P"].y.position + 9 - 1 - 3 * is_q_rolled, n_elements=1
        )  # Move (yP)_1
        verify_gradient += Script.parse_string("OP_NEGATE") if stack_elements["P"].y.negate else Script()
        verify_gradient += Script.parse_string("OP_TUCK OP_SUB")  # Duplicate (yP_)_1 and compute (yQ_)_1 - (yP_)_1
        # Stack in: q .. lambda .. P .. Q .. lambda xP xQ [lambda * (xP - xQ)] (yP_)_1 [(yQ_)_1 - (yP_)_1]
        # Stack out: q .. lambda .. P .. Q .. lambda xP xQ (yP_)_1 (yP_)_0, or fail
        verify_gradient += stack_elements["Q"].y.move(
            position=stack_elements["Q"].y.position + 10 - 1 * is_q_rolled, n_elements=1
        )  # Move (yQ)_0
        verify_gradient += Script.parse_string("OP_NEGATE") if stack_elements["Q"].y.negate else Script()
        verify_gradient += stack_elements["P"].y.move(
            position=stack_elements["P"].y.position + 11 - 4 * is_q_rolled - 1 * is_p_rolled, n_elements=1
        )  # Move (yP)_0
        verify_gradient += Script.parse_string("OP_NEGATE") if stack_elements["P"].y.negate else Script()
        verify_gradient += Script.parse_string("OP_TUCK OP_SUB")  # Duplicate (yP_)_0 and compute (yQ_)_0 - (yP_)_0
        verify_gradient += roll(position=2, n_elements=1)  # Bring [(yQ_)_1 - (yP_)_1] on top
        verify_gradient += roll(position=5, n_elements=2)  # Bring [lambda * (xP - xQ)] on top
        verify_gradient += fq2.add(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda * (x_P - x_Q) + (yQ_ - yP_)
        verify_gradient += Script.parse_string("OP_CAT OP_0 OP_EQUALVERIFY")

        # Compute x-coordinate of P_ + Q_
        # Stack in: q .. lambda .. P .. Q .. lambda xP xQ (yP_)_1 (yP_)_0
        # Stack out: q .. lambda .. P .. Q .. xP lambda x(P_ + Q_)
        # Altstack out: [(yP_)_0, (yP_)_1]
        x_coordinate = Script.parse_string(" ".join(["OP_TOALTSTACK"] * 2))  # Put (yP_)_0, (yP_)_1 on the altstack
        x_coordinate += pick(position=3, n_elements=2)  # Duplicate xP
        x_coordinate += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)  # Compute (xP + xQ)
        x_coordinate += Script.parse_string("OP_2ROT OP_2SWAP OP_2OVER")  # Roll lambda, reorder, duplicate lambda
        x_coordinate += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute lambda^2
        x_coordinate += Script.parse_string("OP_2SWAP")  # Swap lambda^2 and (xP + xQ)
        x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda^2 - (xP + xQ)

        # Compute y-coordinate of P_ + Q_
        # Stack in: q .. lambda .. P .. Q .. xP lambda x(P_ + Q_)
        # Altstack in: [(yP_)_0, (yP_)_1]
        # Stack out: q .. lambda .. P .. Q .. x(P_ + Q_) y(P_ + Q_)
        # Altstack out: []
        y_coordinate = Script.parse_string("OP_2ROT OP_2OVER")  # Rotate xP, duplicate x(P_ + Q_)
        y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=5, n_elements=2)  # Bring lambda on top
        y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda * (xP - x(P_+Q_))
        y_coordinate += Script.parse_string("OP_FROMALTSTACK OP_SUB")  # Compute [lambda * (xP - x(P_+Q_))]_1 - (yP_)_1
        if take_modulo:
            y_coordinate += Script.parse_string("OP_DEPTH OP_1SUB")
            y_coordinate += Script.parse_string("OP_ROLL") if clean_constant else Script.parse_string("OP_PICK")
            y_coordinate += Script.parse_string(
                "OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD"
            )  # Compute {[lambda * (xP - x(P_+Q_))]_1 - (yP_)_1} % q
            y_coordinate += roll(position=2, n_elements=1)  # Bring [lambda * (xP - x(P_+Q_))]_0 on top
            y_coordinate += Script.parse_string(
                "OP_FROMALTSTACK OP_SUB"
            )  # Compute [lambda * (xP - x(P_+Q_))]_0 - (yP_)_0
            y_coordinate += Script.parse_string(
                "OP_ROT OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD"
            )  # Compute {[lambda * (xP - x(P_+Q_))]_0 - (yP_)_0} % q
        else:
            y_coordinate += roll(position=1, n_elements=1)  # Bring lambda * (xP - x(P_+Q_))]_0 on top
            y_coordinate += Script.parse_string(
                "OP_FROMALTSTACK OP_SUB"
            )  # Compute [lambda * (xP - x(P_+Q_))]_0 - (yP_)_0
        y_coordinate += roll(
            position=1, n_elements=1
        )  # Swap {[lambda * (xP - x(P_+Q_))]_0 - (yP_)_0} and {[lambda * (xP - x(P_+Q_))]_1 - (yP_)_1}

        out += verify_gradient + x_coordinate + y_coordinate
        return out

    def point_algebraic_addition_without_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq2.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q` without
        verifying the gradient provided.
        If `take_modulo` is set to `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P .. Q ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. {Q} .. (P_+ Q_)]
        - altstack = []

        where {-} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = P if not P.y.negate else -P
        Q_ = Q if not Q.y.negate else -Q

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None, optional): If `True`, check if the constant (q) is valid before proceeding.
            clean_constant (bool | None, optional): If `True`, clean the constant by removing it
                from the stack after use.
            stack_elements (StackElements | None, optional): Dictionary with keys:
                - lambda (StackNumber): The position of gradient through P_ and Q_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - Q (StackEllipticCurvePoint): The position of the point `Q` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                If None, the default dictionary is:
                    stack_elements = {
                        "lambda" : StackNumber(9,2,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(7,2,False,roll),StackNumber(5,2,False,roll)),
                        "Q" : StackEllipticCurvePoint(StackNumber(3,2,False,roll),StackNumber(1,2,False,roll)),
                    }

        Returns:
            A Bitcoin Script that computes P_ + Q_ for the given elliptic curve points `P` and `Q`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `lambda` comes after `P` in the stack
                - `P` comes after `Q` in the stack
                - `stack_elements` is not None, but it does not contain all the keys `lambda`, `P`, `Q`

        Preconditions:
            - The input points `P` and `Q` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P_` != `Q_` and `P_ != -Q_` and `P_`, `Q_` not the point at infinity

        Notes:
            This function assumes the input points are represented as minimally encoded, little-endian integers.
            This function does not check the validity of the gradient provided.

        """
        stack_elements = (
            {
                "lambda": StackNumber(9, 2, False, roll),
                "P": StackEllipticCurvePoint(StackNumber(7, 2, False, roll), StackNumber(5, 2, False, roll)),
                "Q": StackEllipticCurvePoint(StackNumber(3, 2, False, roll), StackNumber(1, 2, False, roll)),
            }
            if stack_elements is None
            else stack_elements
        )
        if "lambda" not in stack_elements or "P" not in stack_elements or "Q" not in stack_elements:
            msg = f"The stack_elements dictionary must have the following keys:\
                'lambda', 'P', 'Q': stack_elements.keys: { stack_elements.keys()}"
            raise ValueError(msg)
        if not stack_elements["lambda"] < stack_elements["P"]:
            msg = "P must come after lambda in the stack"
            raise ValueError(msg)
        if not stack_elements["P"] < stack_elements["Q"]:
            msg = "Q must come after P in the stack"
            raise ValueError(msg)
        is_q_rolled = stack_elements["Q"].x.move == roll

        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Fq2 implementation
        fq2 = self.FQ2

        # Write:
        #   P_ = P if not P.y.negate else -P
        #   Q_ = Q if not Q.y.negate else -Q

        # Compute x-coordinate of P_ + Q_
        # Stack in: q .. lambda .. P .. Q ..
        # Stack out: q .. lambda .. P .. Q .. lambda xP x(P_+Q_)
        x_coordinate = stack_elements["lambda"].move(
            position=stack_elements["lambda"].position, n_elements=2
        )  # Move lambda
        x_coordinate += pick(position=1, n_elements=2)  # Duplicate lambda
        x_coordinate += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute lambda^2
        x_coordinate += stack_elements["P"].x.move(position=stack_elements["P"].x.position + 4, n_elements=2)  # Move xP
        x_coordinate += stack_elements["Q"].x.move(position=stack_elements["Q"].x.position + 6, n_elements=2)  # Move xQ
        x_coordinate += pick(position=3, n_elements=2)  # Duplicate xP
        x_coordinate += fq2.add(take_modulo=False, check_constant=False, clean_constant=False)  # Compute (xP + xQ)
        x_coordinate += roll(position=5, n_elements=2)  # Bring lambda^2 on top
        x_coordinate += roll(position=3, n_elements=2)  # Bring (xP + xQ) on top
        x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda^2 - (xP + xQ)

        # Compute y-coordinate of P_ + Q_
        # Stack in: q .. lambda .. P .. Q .. lambda xP x(P_ + Q_)
        # Stack out: q .. lambda .. P .. Q .. x(P_ + Q_) y(P_ + Q_)
        y_coordinate = Script.parse_string("OP_2SWAP OP_2OVER")  # Rotate xP, duplicate x(P_ + Q_)
        y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=5, n_elements=2)  # Bring lambda on top
        y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda * (xP - x(P_+Q_))
        y_coordinate += Script.parse_string("OP_TOALTSTACK")
        y_coordinate += stack_elements["P"].y.move(
            position=stack_elements["P"].y.position + 3 - 2 * is_q_rolled, n_elements=1
        )  # Move yP_0
        y_coordinate += Script.parse_string("OP_ADD" if stack_elements["P"].y.negate else "OP_SUB")
        if take_modulo:
            if clean_constant:
                y_coordinate += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
            else:
                y_coordinate += Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            y_coordinate += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
        y_coordinate += Script.parse_string("OP_FROMALTSTACK")
        y_coordinate += stack_elements["P"].y.move(
            position=stack_elements["P"].y.position + 4 - 1 - 2 * is_q_rolled + 1 * take_modulo, n_elements=1
        )  # Move yP_1
        y_coordinate += Script.parse_string("OP_ADD" if stack_elements["P"].y.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += Script.parse_string("OP_ROT OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD")

        drop_yq = stack_elements["Q"].y.move(position=stack_elements["Q"].y.position + 4, n_elements=2)  # Move yQ
        drop_yq += Script.parse_string("OP_2DROP")

        out += x_coordinate + y_coordinate
        if is_q_rolled:
            out += drop_yq  # Drop yQ
        if clean_constant and not take_modulo:
            out += Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL OP_DROP")

        return out

    def point_algebraic_doubling_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq2.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        If `take_modulo` is set to `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. 2P_]
        - altstack = []

        where {-} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = P if not P.y.negate else -P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None, optional): If `True`, check if the constant (q) is valid before proceeding.
            clean_constant (bool | None, optional): If `True`, clean the constant by removing it
                from the stack after use.
            stack_elements (StackElements | None, optional): Dictionary with keys:
                - lambda (StackNumber): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                If None, the default dictionary is:
                    stack_elements = {
                        "lambda" : StackNumber(5,2,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(3,2,False,roll),StackNumber(1,2,False,roll)),
                    }

        Returns:
            A Bitcoin Script that computes 2P_ for the given elliptic curve points `P`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `lambda` comes after `P` in the stack
                - `stack_elements` is not None, but it does not contain all the keys `lambda`, `P`

        Preconditions:
            - The input point `P` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P` not the point at infinity

        Notes:
            This function assumes the input points are represented as minimally encoded, little-endian integers.

        """
        stack_elements = (
            {
                "lambda": StackNumber(5, 2, False, roll),
                "P": StackEllipticCurvePoint(StackNumber(3, 2, False, roll), StackNumber(1, 2, False, roll)),
            }
            if stack_elements is None
            else stack_elements
        )
        if "lambda" not in stack_elements or "P" not in stack_elements:
            msg = f"The stack_elements dictionary must have the following keys:\
                'lambda', 'P': stack_elements.keys: { stack_elements.keys()}"
            raise ValueError(msg)
        if not stack_elements["lambda"] < stack_elements["P"]:
            msg = "P must come after lambda in the stack"
            raise ValueError(msg)
        is_p_rolled = stack_elements["P"].x.move == roll

        # Fq2 implementation
        fq2 = self.FQ2
        # A coefficient
        curve_a = self.CURVE_A

        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Write:
        #   P_ = P if not P.y.negate else -P

        # Verify that lambda is the gradient of the line tangent at P_
        # Stack in: q .. lambda .. P ..
        # Stack out: q .. lambda .. P .. lambda yP lambda yP
        verify_gradient = stack_elements["lambda"].move(
            position=stack_elements["lambda"].position, n_elements=2
        )  # Move lambda
        verify_gradient += stack_elements["P"].y.move(
            position=stack_elements["P"].y.position + 2, n_elements=2
        )  # Move yP
        verify_gradient += pick(position=3, n_elements=4)  # Duplicate lambda and xP
        # Stack in: q .. lambda .. P .. lambda yP lambda yP
        # Stack out: q .. lambda .. P .. lambda yP (2*lambda*yP_)
        verify_gradient += fq2.mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute lamdba * yP
        verify_gradient += Script.parse_string("OP_2")
        if stack_elements["P"].y.negate:
            verify_gradient += Script.parse_string("OP_NEGATE")
        verify_gradient += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)
        # Stack in: q .. lambda .. P .. lambda yP (2*lambda*yP_)
        # Stack out: q .. lambda .. P .. lambda yP xP, or fail
        verify_gradient += stack_elements["P"].x.move(
            position=stack_elements["P"].x.position + 6 - 2 * is_p_rolled, n_elements=2
        )  # Move xP
        verify_gradient += roll(position=3, n_elements=2)  # Bring (2*lambda*yP_) on top
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
        )  # Compute 2*lambda*yP_ - (3xP^2 + a)
        verify_gradient += Script.parse_string("OP_CAT OP_0 OP_EQUALVERIFY")

        # Compute x-coordinate of 2P_
        # Stack in: q .. lambda .. P .. lambda yP xP
        # Stack out: q .. lambda .. P .. yP lambda xP x(2P_)
        x_coordinate = roll(position=5, n_elements=2)  # Bring lambda on top
        x_coordinate += pick(position=1, n_elements=2)  # Duplicate lambda
        x_coordinate += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute lambda^2
        x_coordinate += roll(position=5, n_elements=2)  # Bring xP on top
        x_coordinate += roll(position=3, n_elements=2)  # Bring lambda on top
        x_coordinate += pick(position=3, n_elements=2)  # Duplicate xP
        x_coordinate += Script.parse_string("OP_2")
        x_coordinate += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute 2 * xP
        x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda^2 - 2*xP

        # Compute y-coordinate of 2P_
        # Stack in: q .. lambda .. P .. yP lambda xP x(2P_)
        # Stack out: q .. lambda .. P .. x(2P_) y(2P_)
        y_coordinate = roll(position=3, n_elements=2)  # Bring xP on top
        y_coordinate += pick(position=3, n_elements=2)  # Duplicate x(2P_) on top
        y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_(2P_)
        y_coordinate += roll(position=5, n_elements=2)  # Bring lambda on top
        y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda * (xP - x_(2P))
        y_coordinate += roll(position=5, n_elements=2)  # Bring yP on top
        y_coordinate += (
            fq2.add(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )
            if stack_elements["P"].y.negate
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
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq2.

        This function computes the algebraic doubling of P for the elliptic curve point `P` without
        verifying the gradient provided.
        If `take_modulo` is set to `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. 2P_]
        - altstack = []

        where {-} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = P if not P.y.negate else -P

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None, optional): If `True`, check if the constant (q) is valid before proceeding.
            clean_constant (bool | None, optional): If `True`, clean the constant by removing it
                from the stack after use.
            stack_elements (StackElements | None, optional): Dictionary with keys:
                - lambda (StackNumber): The position of gradient of the line tangent at P_ in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                - P (StackEllipticCurvePoint): The position of the point `P` in the stack,
                    its length, whether it should be negated, and whether it should be rolled or picked
                If None, the default dictionary is:
                    stack_elements = {
                        "lambda" : StackNumber(5,2,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(3,2,False,roll),StackNumber(1,2,False,roll)),
                    }

        Returns:
            A Bitcoin Script that computes 2P_ for the given elliptic curve points `P`.

        Raises:
            ValueError: If either of the following happens:
                - `clean_constant` or `check_constant` are not provided when required.
                - `lambda` comes after `P` in the stack
                - `stack_elements` is not None, but it does not contain all the keys `lambda`, `P`

        Preconditions:
            - The input point `P` must be on the elliptic curve.
            - The modulo q must be a prime number.
            - `P` not the point at infinity

        Notes:
            This function assumes the input points are represented as minimally encoded, little-endian integers.
            This function does not check the validity of the gradient provided.

        """
        stack_elements = (
            {
                "lambda": StackNumber(5, 2, False, roll),
                "P": StackEllipticCurvePoint(StackNumber(3, 2, False, roll), StackNumber(1, 2, False, roll)),
            }
            if stack_elements is None
            else stack_elements
        )
        if "lambda" not in stack_elements or "P" not in stack_elements:
            msg = f"The stack_elements dictionary must have the following keys:\
                'lambda', 'P': stack_elements.keys: { stack_elements.keys()}"
            raise ValueError(msg)
        if not stack_elements["lambda"] < stack_elements["P"]:
            msg = "P must come after lambda in the stack"
            raise ValueError(msg)

        # Fq2 implementation
        fq2 = self.FQ2

        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Write:
        #   P_ = P if not P.y.negate else -P

        # Compute x-coordinate of 2P_
        # Stack in: q .. lambda .. P ..
        # Stack out: q .. lambda .. P .. lambda xP x(2P_)
        x_coordinate = stack_elements["lambda"].move(
            position=stack_elements["lambda"].position, n_elements=2
        )  # Move lambda
        x_coordinate += pick(position=1, n_elements=2)  # Duplicate lambda
        x_coordinate += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute lambda^2
        x_coordinate += stack_elements["P"].x.move(
            position=stack_elements["P"].x.position + 4, n_elements=2
        )  # Bring xP on top
        x_coordinate += pick(position=1, n_elements=2)  # Duplicate xP
        x_coordinate += Script.parse_string("OP_2")
        x_coordinate += fq2.scalar_mul(take_modulo=False, check_constant=False, clean_constant=False)  # Compute 2 * xP
        x_coordinate += roll(position=5, n_elements=2)  # Bring lambda^2 on top
        x_coordinate += roll(position=3, n_elements=2)  # Swap 2xP and lambda^2
        x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda^2 - 2*xP

        # Compute y-coordinate of 2P_
        # Stack in: q .. lambda .. P .. lambda xP x(2P_)
        # Stack out: q .. lambda .. P .. x(2P_) y(2P_)
        y_coordinate = roll(position=3, n_elements=2)  # Bring xP on top
        y_coordinate += pick(position=3, n_elements=2)  # Duplicate x(2P_)
        y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_(2P_)
        y_coordinate += roll(position=5, n_elements=2)  # Bring lambda on top
        y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda * (xP - x_(2P))
        y_coordinate += stack_elements["P"].y.move(
            position=stack_elements["P"].y.position + 4, n_elements=2
        )  # Bring yP on top
        y_coordinate += (
            fq2.add(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )
            if stack_elements["P"].y.negate
            else fq2.subtract(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )
        )  # Compute y_(2P)

        out += x_coordinate + y_coordinate

        return out

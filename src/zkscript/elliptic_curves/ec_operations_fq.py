from tx_engine import Script

from src.zkscript.types.stack_elements import StackElements, StackEllipticCurvePoint, StackNumber
from src.zkscript.util.utility_scripts import mod, nums_to_script, pick, roll, verify_bottom_constant


class EllipticCurveFq:
    """Elliptic curve arithmetic over Fq."""

    def __init__(self, q: int, curve_a: int):
        # Characteristic of the field over which the curve is defined
        self.MODULUS = q
        # A coefficient of the curve over which we are performing the operations
        self.CURVE_A = curve_a

    def point_algebraic_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        verify_gradient: bool = True,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        The function branches according to the value of verify_gradient.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P .. Q ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. {Q} .. (P_+ Q_)]
        - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

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
                        "lambda" : StackNumber(4,1,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(3,1,False,roll),StackNumber(2,1,False,roll)),
                        "Q" : StackEllipticCurvePoint(StackNumber(1,1,False,roll),StackNumber(0,1,False,roll)),
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
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        The function branches according to the value of verify_gradient.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. 2P_]
        - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P

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

    def point_algebraic_addition_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P .. Q ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. {Q} .. (P_+ Q_)]
        - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

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
                        "lambda" : StackNumber(4,1,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(3,1,False,roll),StackNumber(2,1,False,roll)),
                        "Q" : StackEllipticCurvePoint(StackNumber(1,1,False,roll),StackNumber(0,1,False,roll)),
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
            - `P_` and `Q_` are not equal, nor inverse, nor the point at infinity

        Notes:
            This function assumes the input points are represented as minimally encoded, little-endian integers.
            If this function is used when `P_` != `Q_` or `P_ != -Q_`, then any lambda will pass
            the gradient verification, but the point computed is not going to be `P_ + Q_`.

        """
        stack_elements = (
            {
                "lambda": StackNumber(4, 1, False, roll),
                "P": StackEllipticCurvePoint(StackNumber(3, 1, False, roll), StackNumber(2, 1, False, roll)),
                "Q": StackEllipticCurvePoint(StackNumber(1, 1, False, roll), StackNumber(0, 1, False, roll)),
            }
            if stack_elements is None
            else stack_elements
        )
        if "lambda" not in stack_elements or "P" not in stack_elements or "Q" not in stack_elements:
            msg = f"The stack_elements dictionary must have the following keys:\
                'lambda', 'P', 'Q': stack_elements.keys: { stack_elements.keys()}"
            raise ValueError(msg)
        if not stack_elements["lambda"].is_before(stack_elements["P"].x):
            msg = "P must come after lambda in the stack"
            raise ValueError(msg)
        if not stack_elements["P"].is_before(stack_elements["Q"]):
            msg = "Q must come after P in the stack"
            raise ValueError(msg)
        is_q_rolled = stack_elements["Q"].x.is_rolled()
        is_p_rolled = stack_elements["P"].x.is_rolled()

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Write:
        #   P_ = -P not P.y.negate else P
        #   Q_ = -Q if Q.y.negate else Q

        # Verify that lambda is the gradient between P_ and Q_
        # Stack in: q .. lambda .. P .. Q ..
        # Stack out: q .. lambda .. P .. Q .. yP xQ xP lambda, or fail
        # Altstack out: [q if take_modulo]
        verify_gradient = stack_elements["Q"].moving_script()  # Move xQ, yQ
        verify_gradient += stack_elements["P"].y.shift(2 - 2 * is_q_rolled).moving_script()  # Move yP
        verify_gradient += Script.parse_string("OP_TUCK")
        if (stack_elements["P"].y.negate and not stack_elements["Q"].y.negate) or (
            not stack_elements["P"].y.negate and stack_elements["Q"].y.negate
        ):
            verify_gradient += Script.parse_string("OP_ADD")  # Compute yQ + yP
        else:
            verify_gradient += Script.parse_string("OP_SUB")  # Compute yQ - yP
        verify_gradient += roll(position=2, n_elements=1)  # Bring xQ on top
        verify_gradient += stack_elements["P"].x.shift(3 - 2 * is_q_rolled - 1 * is_p_rolled).moving_script()  # Move xP
        verify_gradient += Script.parse_string("OP_2DUP OP_SUB")  # Duplicate xP, xQ, compute xQ - xP
        verify_gradient += (
            stack_elements["lambda"].shift(5 - 2 * is_p_rolled - 2 * is_q_rolled).moving_script()
        )  # Move lambda
        verify_gradient += Script.parse_string("OP_TUCK OP_MUL")  # Compute lambda *(xP - xQ)
        verify_gradient += roll(position=4, n_elements=1)  # Bring yQ + yP or yQ - yP on top
        if (stack_elements["P"].y.negate and not stack_elements["Q"].y.negate) or (
            not stack_elements["P"].y.negate and not stack_elements["Q"].y.negate
        ):
            verify_gradient += Script.parse_string("OP_SUB")  # Compute lambda *(xP - xQ) - (yP_ - yQ_)
        else:
            verify_gradient += Script.parse_string("OP_ADD")  # Compute lambda *(xP - xQ) - (yP_ - yQ_)
        verify_gradient += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
        verify_gradient += mod(stack_preparation="")
        verify_gradient += Script.parse_string("OP_0 OP_EQUALVERIFY")
        verify_gradient += Script.parse_string("OP_TOALTSTACK" if take_modulo else "OP_DROP")

        # Compute x(P_+Q_) = lambda^2 - x_P - x_Q
        # Stack in: q .. lambda .. P .. Q .. yP xQ xP lambda
        # Altstack in: [q if take_modulo]
        # Stack out: q .. lambda .. P .. Q .. yP lambda x(P_+Q_)
        # Altstack out: [q if take_modulo, xP]
        x_coordinate = Script.parse_string("OP_DUP OP_DUP OP_MUL")  # Duplicate lambda and compute lambda^2
        x_coordinate += Script.parse_string("OP_2SWAP OP_TUCK")  # Swap lambda, lambda^2 and xQ, xP, duplicate xP
        x_coordinate += Script.parse_string(
            "OP_TOALTSTACK OP_ADD OP_SUB"
        )  # Put xP on altstack, compute lambda^2 - (xQ + xP)

        # Compute y(P_+Q_) = lambda * (xP - x(P_+Q_)) - yP_
        # Stack in: q .. lambda .. P .. Q .. yP lambda x(P_+Q_)
        # Altstack in: [q if take_modulo, xP]
        # Stack out: q .. lambda .. P .. Q .. x(P_+Q_) y(P_+Q_)
        # Altstack out: []
        y_coordinate = Script.parse_string("OP_FROMALTSTACK")  # Pull xP from altstack
        y_coordinate += pick(position=1, n_elements=1)  # Duplicate x(P_+Q_)
        y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=2, n_elements=1)  # Bring lambda on top
        y_coordinate += Script.parse_string("OP_MUL")  # Compute lambda * (xP - x(P_+Q_))
        y_coordinate += roll(position=2, n_elements=1)  # Bring yP on top
        y_coordinate += Script.parse_string("OP_ADD" if stack_elements["P"].y.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += Script.parse_string("OP_FROMALTSTACK")  # Pull q from altstack
            y_coordinate += mod(stack_preparation="")
            y_coordinate += Script.parse_string("OP_TOALTSTACK")
            y_coordinate += mod(stack_preparation="", is_constant_reused=False)
            y_coordinate += Script.parse_string("OP_FROMALTSTACK")

        out += verify_gradient + x_coordinate + y_coordinate
        return out

    def point_algebraic_addition_without_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic addition of points on an elliptic curve defined over Fq.

        This function computes the algebraic addition of P and Q for elliptic curve points `P` and `Q`.
        This functions does not verify the validity of the gradient provided.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P .. Q ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. {Q} .. (P_+ Q_)]
        - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P
        Q_ = -Q if Q.y.negate else Q

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
                        "lambda" : StackNumber(4,1,False,roll),
                        "P" : StackEllipticCurvePoint(StackNumber(3,1,False,roll),StackNumber(2,1,False,roll)),
                        "Q" : StackEllipticCurvePoint(StackNumber(1,1,False,roll),StackNumber(0,1,False,roll)),
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
            - `P_` and `Q_` are not equal, nor inverse, nor the point at infinity

        Notes:
            This function assumes the input points are represented as minimally encoded, little-endian integers.

        """
        stack_elements = (
            {
                "lambda": StackNumber(4, 1, False, roll),
                "P": StackEllipticCurvePoint(StackNumber(3, 1, False, roll), StackNumber(2, 1, False, roll)),
                "Q": StackEllipticCurvePoint(StackNumber(1, 1, False, roll), StackNumber(0, 1, False, roll)),
            }
            if stack_elements is None
            else stack_elements
        )
        if "lambda" not in stack_elements or "P" not in stack_elements or "Q" not in stack_elements:
            msg = f"The stack_elements dictionary must have the following keys:\
                'lambda', 'P', 'Q': stack_elements.keys: { stack_elements.keys()}"
            raise ValueError(msg)
        if not stack_elements["lambda"].is_before(stack_elements["P"].x):
            msg = "P must come after lambda in the stack"
            raise ValueError(msg)
        if not stack_elements["P"].is_before(stack_elements["Q"]):
            msg = "Q must come after P in the stack"
            raise ValueError(msg)
        is_q_rolled = stack_elements["Q"].x.is_rolled()
        is_p_rolled = stack_elements["P"].x.is_rolled()

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Write:
        #   P_ = -P not P.y.negate else P
        #   Q_ = -Q if Q.y.negate else Q

        drop_yq = stack_elements["Q"].y.moving_script()  # Move yQ
        drop_yq += Script.parse_string("OP_DROP")
        if is_q_rolled:
            out += drop_yq

        # Compute x(P_+Q_) = lambda^2 - x_P - x_Q
        # Stack in: q .. lambda .. P .. Q ..
        # Stack out: q .. lambda .. P .. Q ..  xP lambda x(P_+Q_)
        x_coordinate = stack_elements["Q"].x.shift(-1 * is_q_rolled).moving_script()  # Move xQ
        x_coordinate += stack_elements["P"].x.shift(1 - 2 * is_q_rolled).moving_script()  # Move xP
        x_coordinate += Script.parse_string("OP_TUCK OP_ADD")  # Duplicate xP, compute xP + xQ
        x_coordinate += (
            stack_elements["lambda"].shift(2 - 2 * is_q_rolled - 1 * is_p_rolled).moving_script()
        )  # Move lambda
        x_coordinate += Script.parse_string("OP_DUP OP_DUP OP_MUL")  # Duplicate almbda, compute lambda^2
        x_coordinate += roll(position=2, n_elements=1)  # Bring xP + xQ on top
        x_coordinate += Script.parse_string("OP_SUB")  # Compute lambda^2 - (xP + xQ)

        # Compute y(P_+Q_) = lambda * (xP - x(P_+Q_)) - yP_
        # Stack in: q .. lambda .. P .. Q ..  xP lambda x(P_+Q_)
        # Stack out: q .. lambda .. P .. Q .. x(P_+Q_) y(P_+Q_)
        y_coordinate = roll(position=2, n_elements=1)  # Bring xP on top
        y_coordinate += pick(position=1, n_elements=1)  # Duplicate x(P_+Q_)
        y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=2, n_elements=1)  # Bring lambda on top
        y_coordinate += Script.parse_string("OP_MUL")  # Compute lambda * (xP - x(P_+Q_))
        y_coordinate += stack_elements["P"].y.shift(2 - 2 * is_q_rolled).moving_script()  # Move yP
        y_coordinate += Script.parse_string("OP_ADD" if stack_elements["P"].y.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += Script.parse_string("OP_TOALTSTACK")
            y_coordinate += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            y_coordinate += mod(stack_preparation="")
            y_coordinate += mod(is_constant_reused=False)

        out += x_coordinate + y_coordinate
        return out

    def point_algebraic_doubling_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. 2P_]
        - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P

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
                "lambda": StackNumber(2, 1, False, roll),
                "P": StackEllipticCurvePoint(StackNumber(1, 1, False, roll), StackNumber(0, 1, False, roll)),
            }
            if stack_elements is None
            else stack_elements
        )
        if "lambda" not in stack_elements or "P" not in stack_elements:
            msg = f"The stack_elements dictionary must have the following keys:\
                'lambda', 'P': stack_elements.keys: { stack_elements.keys()}"
            raise ValueError(msg)
        if not stack_elements["lambda"].is_before(stack_elements["P"].x):
            msg = "P must come after lambda in the stack"
            raise ValueError(msg)
        is_p_rolled = stack_elements["P"].is_rolled()

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        curve_a = self.CURVE_A

        # Verify that lambda is the gradient between P_ and Q_
        # Stack in: q .. lambda .. P ..
        # Stack out: q .. lambda .. P .. xP yP lambda, or fail
        # Altstack out: [q if take_modulo]
        verify_gradient = stack_elements["P"].moving_script()  # Move xP, yP
        verify_gradient += pick(position=1, n_elements=2)  # Duplicate xP, yP
        verify_gradient += Script.parse_string("OP_2 OP_MUL")  # Compute 2yP
        verify_gradient += stack_elements["lambda"].shift(4 - 2 * is_p_rolled).moving_script()  # Move lambda
        verify_gradient += Script.parse_string("OP_TUCK")  # Duplicate lambda
        verify_gradient += Script.parse_string("OP_MUL")  # Compute 2yP * lambda
        verify_gradient += roll(position=2, n_elements=1)  # Bring xP on top
        verify_gradient += Script.parse_string("OP_DUP OP_MUL")  # Compute xP^2
        verify_gradient += Script.parse_string("OP_3 OP_MUL")  # Compute 3*xP^2
        if curve_a:
            verify_gradient += nums_to_script([curve_a])
            verify_gradient += Script.parse_string("OP_ADD")
        verify_gradient += Script.parse_string("OP_ADD" if stack_elements["P"].y.negate else "OP_SUB")
        verify_gradient += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
        verify_gradient += mod(stack_preparation="")
        verify_gradient += Script.parse_string("OP_0 OP_EQUALVERIFY")
        verify_gradient += Script.parse_string("OP_TOALTSTACK" if take_modulo else "OP_DROP")

        # Compute x(P_+Q_) = lambda^2 - 2*x_P
        # Stack in: q .. lambda .. P .. xP yP lambda
        # Altstack in: [q if take_modulo]
        # Stack out: q .. lambda .. P .. Q ..  lambda xP x(P_+Q_)
        # Altstack out: [q if take_modulo, yP]
        x_coordinate = Script.parse_string("OP_DUP OP_DUP OP_MUL")  # Duplicate lambda, compute lambda^2
        x_coordinate += roll(position=3, n_elements=2)  # Bring xP, yP on top
        x_coordinate += Script.parse_string("OP_TOALTSTACK")  # Put yP on altstack
        x_coordinate += Script.parse_string("OP_TUCK")  # Duplicate xP
        x_coordinate += Script.parse_string("OP_2 OP_MUL OP_SUB")  # Compute lambda^2 - 2*x_P

        # Compute x(P_+Q_) = lambda^2 - 2*x_P
        # Stack in: q .. lambda .. P ..  lambda xP x(P_+Q_)
        # Altstack in: [q if take_modulo, yP]
        # Stack out: q .. lambda .. P ..  x(P_+Q_) y(P_+Q_)
        # Altstack out: []
        y_coordinate = roll(position=1, n_elements=1)  # Bring xP on top
        y_coordinate += pick(position=1, n_elements=1)  # Duplicate x(P_+Q_)
        y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=2, n_elements=1)  # Bring lambda on top
        y_coordinate += Script.parse_string("OP_MUL")  # Compute lambda * (xP - x(P_+Q_))
        y_coordinate += Script.parse_string("OP_FROMALTSTACK")  # Pull yP from altstack
        y_coordinate += Script.parse_string("OP_ADD" if stack_elements["P"].y.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += Script.parse_string("OP_FROMALTSTACK")  # Pull q from altstack
            y_coordinate += mod(stack_preparation="")
            y_coordinate += Script.parse_string("OP_TOALTSTACK")
            y_coordinate += mod(stack_preparation="", is_constant_reused=False)
            y_coordinate += Script.parse_string("OP_FROMALTSTACK")

        out += verify_gradient + x_coordinate + y_coordinate
        return out

    def point_algebraic_doubling_without_verifying_gradient(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        stack_elements: StackElements | None = None,
    ) -> Script:
        """Perform algebraic point doubling of points on an elliptic curve defined over Fq.

        This function computes the algebraic doubling of P for the elliptic curve points `P`.
        This function does not verify the validity of the gradient provided.
        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> .. P ..]
        - altstack = []

        Stack output:
        - stack    = [q .. {<lambda>} .. {P} .. 2P_]
        - altstack = []

        where {P} means that the element is there if it is picked, it is not there if it is rolled.
        P_ = -P not P.y.negate else P

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
                "lambda": StackNumber(2, 1, False, roll),
                "P": StackEllipticCurvePoint(StackNumber(1, 1, False, roll), StackNumber(0, 1, False, roll)),
            }
            if stack_elements is None
            else stack_elements
        )
        if "lambda" not in stack_elements or "P" not in stack_elements:
            msg = f"The stack_elements dictionary must have the following keys:\
                'lambda', 'P': stack_elements.keys: { stack_elements.keys()}"
            raise ValueError(msg)
        if not stack_elements["lambda"].is_before(stack_elements["P"].x):
            msg = "P must come after lambda in the stack"
            raise ValueError(msg)
        is_p_rolled = stack_elements["P"].is_rolled()

        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        # Compute x(P_+Q_) = lambda^2 - 2*x_P
        # Stack in: q .. lambda .. P ..
        # Stack out: q .. lambda .. P ..  xP yP lambda x(2P_)
        x_coordinate = stack_elements["P"].moving_script()  # Move xP, yP
        x_coordinate += Script.parse_string("OP_OVER OP_2 OP_MUL")  # Duplicate xP, compute 2xP
        x_coordinate += stack_elements["lambda"].shift(3 - 2 * is_p_rolled).moving_script()  # Move lambda
        x_coordinate += Script.parse_string("OP_TUCK OP_DUP OP_MUL")  # Duplicate lambda, compute lamdba^2
        x_coordinate += Script.parse_string("OP_SWAP OP_SUB")  # Compute lambda^2 - 2*x_P

        # Compute y(P_+Q_) = lambda * (xP - x(P_+Q_)) - yP_
        # Stack in: q .. lambda .. P ..  xP yP lambda x(2P_)
        # Stack out: q .. lambda .. P .. Q ..  x(P_+Q_) y(P_+Q_)
        # Altstack out: []
        y_coordinate = roll(position=3, n_elements=1)  # Bring xP on top
        y_coordinate += pick(position=1, n_elements=1)  # Duplicate x(P_+Q_)
        y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x(P_+Q_)
        y_coordinate += roll(position=2, n_elements=1)  # Bring lambda on top
        y_coordinate += Script.parse_string("OP_MUL")  # Compute lambda * (xP - x(P_+Q_))
        y_coordinate += roll(position=2, n_elements=1)  # Pull yP from altstack
        y_coordinate += Script.parse_string("OP_ADD" if stack_elements["P"].y.negate else "OP_SUB")
        if take_modulo:
            y_coordinate += Script.parse_string("OP_TOALTSTACK")
            y_coordinate += roll(position=-1, n_elements=1) if clean_constant else pick(position=-1, n_elements=1)
            y_coordinate += mod(stack_preparation="")
            y_coordinate += mod(is_constant_reused=False)

        out += x_coordinate + y_coordinate
        return out

    def point_addition_with_unknown_points(
        self, take_modulo: bool, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Sum two points which we do not know whether they are equal, different, or the inverse of one another.

        If `take_modulo` is `True`, the result is reduced modulo `q`.
        It also handles optional checks on the curve constant and whether the constant should be cleaned or reused.

        Stack input:
        - stack    = [q .. <lambda> P Q]
        - altstack = []

        Stack output:
        - stack    = [q .. <lambda> (P + Q)]
        - altstack = []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo q.
            check_constant (bool | None, optional): If `True`, check if the constant (q) is valid before proceeding.
            clean_constant (bool | None, optional): If `True`, clean the constant by removing it
                from the stack after use.

        Returns:
            A Bitcoin script that compute the sum of `P` and `Q`, handling all possibilities.

        Preconditions:
            - P and Q are points on F_q
            - If P != -Q, then lambda is the gradient of the line through P and Q
            - If P = -Q or P is the point at infinity, or Q is the point at infinity, then do not put lambda

        Notes:
            If P = -Q, then we return 0x00 0x00, i.e., we encode the point at infinity as (0x00,0x00) (notice that
            these are data payloads, they are not numbers - points are assumed to be passed as numbers, which means that
            (0,0) would have to be passed as OP_0 OP_0)

        """
        out = verify_bottom_constant(self.MODULUS) if check_constant else Script()

        curve_a = self.CURVE_A

        # Check if Q or P is point at infinity or if P = - Q -----------------------------------------------------------
        # After this, the stack is: <lambda> P Q

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

        # Validate lambda ----------------------------------------------------------------------------------------------
        # After this, the stack is: <lambda> P Q, altstack = [Verify(lambda)]

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
        out += pick(position=3, n_elements=1)  # Pick lambda
        out += Script.parse_string("OP_MUL")  # Compute 2 lambda y_P
        out += pick(position=2, n_elements=1)  # Pick x_P
        out += Script.parse_string("OP_DUP")  # Duplicate x_P
        out += Script.parse_string("OP_MUL")  # Compute x_P^2
        out += Script.parse_string("OP_3 OP_MUL")  # Compute 3 x_P^2
        if curve_a != 0:
            out += nums_to_script([curve_a]) + Script.parse_string("OP_ADD")  # Compute 3 x_P^2 + a if a != 0
        out += Script.parse_string("OP_SUB")

        # If P != Q:
        out += Script.parse_string("OP_ELSE")
        out += pick(position=4, n_elements=2)  # Pick lambda and x_P
        out += Script.parse_string("OP_MUL OP_ADD")  # compute lambda x_P + y_Q
        out += Script.parse_string("OP_OVER OP_5 OP_PICK OP_MUL OP_3 OP_PICK OP_ADD")  # compute lambda x_Q + y_P
        out += Script.parse_string("OP_SUB")
        out += Script.parse_string("OP_ENDIF")

        # Place on the altstack
        out += Script.parse_string("OP_TOALTSTACK")

        # End of lambda validation -------------------------------------------------------------------------------------

        # Calculation of P + Q
        # After this, the stack is: (P+Q), altstack = [Verify(lambda)]

        # Compute x_(P+Q) = lambda^2 - x_P - x_Q
        # After this, the base stack is: <lambda> x_P y_P x_(P+Q), altstack = [Verify(lambda)]
        compute_x_coordinate = Script.parse_string("OP_2OVER")
        compute_x_coordinate += Script.parse_string("OP_SWAP")
        compute_x_coordinate += Script.parse_string("OP_DUP OP_MUL")  # Compute lambda^2
        compute_x_coordinate += Script.parse_string("OP_ROT OP_ROT OP_ADD OP_SUB")  # Compute lambda^2 - (x_P + x_Q)

        # Compute y_(P+Q) = lambda (x_P - x_(P+Q)) - y_P
        # After this, the stack is: x_(P+Q) y_(P+Q), altstack = [Verify(lambda)]
        compute_y_coordinate = Script.parse_string("OP_TUCK")
        compute_y_coordinate += Script.parse_string("OP_2SWAP")
        compute_y_coordinate += Script.parse_string("OP_SUB")  # Compute xP - x_(P+Q)
        compute_y_coordinate += Script.parse_string("OP_2SWAP OP_TOALTSTACK")
        compute_y_coordinate += Script.parse_string(
            "OP_MUL OP_FROMALTSTACK OP_SUB"
        )  # Compute lambda (x_P - x_(P+Q)) - y_P

        # After this, the stack is: (P+Q) q, altstack = [Verify(lambda)]
        out += compute_x_coordinate + compute_y_coordinate + pick(position=-1, n_elements=1)

        batched_modulo = mod(stack_preparation="")  # Mod y
        batched_modulo += Script.parse_string("OP_TOALTSTACK")
        batched_modulo += mod(stack_preparation="")  # Mod x
        batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")

        # If needed, mod out
        # After this, the stack is: (P+Q) q, altstack = [Verify(lambda)] with the coefficients in Fq (if executed)
        if take_modulo:
            out += batched_modulo

        check_lambda = Script.parse_string("OP_FROMALTSTACK")
        check_lambda += mod(stack_preparation="", is_mod_on_top=False, is_constant_reused=False)
        check_lambda += Script.parse_string("OP_0 OP_EQUALVERIFY")

        # Check lambda was correct
        out += check_lambda

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

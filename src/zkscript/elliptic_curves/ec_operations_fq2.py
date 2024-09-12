from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script, roll


class EllipticCurveFq2:
    """Elliptic curve arithmetic over Fq2."""

    def __init__(self, q: int, curve_a: list[int], fq2):
        # Characteristic of the field over which the curve is defined
        self.MODULUS = q
        # A coefficient of the curve over which we carry out the operations, as a list of integers
        self.CURVE_A = curve_a
        # Fq2 implementation in script
        self.FQ2 = fq2

    def point_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        position_lambda: int = 9,
        position_p: int = 7,
        position_q: int = 3,
    ) -> Script:
        """Point addition.

        Input Parameters:
            - Stack: q .. <lambda> .. P .. Q ..
            - Altstack: []
        Output:
            - P + Q
        Assumption on parameters:
            - P and Q are points on E(F_q^2), passed as couple of elements of Fq2
            - lambda is the gradient of the line through P and Q, passed as an element in Fq2
            - P != Q --> It is very important that this assumption is satisfied, otherwise any lambda will pass the test
            if P == Q
            - P != -Q --> It is very important that this assumption is satisfied, otherwise lambda = 0 will pass the
            test
            - P and Q are not the point at infinity --> This function is not able to handle such case
            - position_lambda, position_p and position_q denote the positions in the stack (top of stack is position 1)
            of the first element of lambda, P, and Q respectively
        Assumption on arguments:
            - position_lambda, position_p, position_q > 0
            - position_lambda > position_p + 1, position_p > position_q + 3

        If take_modulo = True, the coordinates of P + Q are in Fq2.

        By default position_lambda = 9, position_p = 7, positon_Q = 3, which means we assume the stack looks as follows:
        .. <lambda> P Q
        namely, we assume the stack has been prepared in advance.
        """
        assert position_lambda > 0, f"Position lambda {position_lambda} must be bigger than 0"
        assert position_p > 0, f"Position P {position_p} must be bigger than 0"
        assert position_q > 0, f"Position Q {position_q} must be bigger than 0"
        assert (
            position_lambda - position_p > 1
        ), f"Position lambda {position_lambda} must be bigger than position P {position_p} plus one"
        assert (
            position_p - position_q > 3  # noqa: PLR2004
        ), f"Position P {position_lambda} must be bigger than position Q {position_p} plus three"

        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Fq2 implementation
        fq2 = self.FQ2

        # P \neq Q, then check that lambda (x_P - x_Q) = (y_P - y_Q)
        # At the end of this part, the stack is: lambda xP xQ yP

        # After this, the stack is: lambda xP lambda xP
        stack_length_added = 0
        lambda_different_points = roll(position=position_lambda, n_elements=2)  # Roll lambda
        stack_length_added += 2
        lambda_different_points += roll(position=position_p + stack_length_added, n_elements=2)  # Roll xP
        stack_length_added += 2
        lambda_different_points += Script.parse_string("OP_2OVER OP_2OVER")  # Duplicate lambda, xP
        stack_length_added += 4
        # After this, the stack is: lambda xP xQ [lambda * (xP - xQ)]
        lambda_different_points += roll(position=position_q + stack_length_added, n_elements=2)  # Roll xQ
        stack_length_added += 2
        lambda_different_points += Script.parse_string("OP_2SWAP OP_2OVER")  # Swap xP and xQ, duplicate xQ
        stack_length_added += 2
        lambda_different_points += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_Q
        stack_length_added -= 2
        lambda_different_points += Script.parse_string("OP_2ROT")  # Bring lambda on top of the stack
        lambda_different_points += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda * (x_P - x_Q)
        stack_length_added -= 2
        # After this, the stack is: lambda xP xQ yP
        lambda_different_points += roll(position=position_q + stack_length_added - 2, n_elements=2)  # Roll yQ
        stack_length_added += 0  # These elements were already in front of P
        lambda_different_points += roll(
            position=position_p + stack_length_added - 2 - 2, n_elements=2
        )  # Roll yP: -2 is for y coordinates, -2 is because xQ was already in front of P
        lambda_different_points += Script.parse_string("OP_2SWAP OP_2OVER")  # Swap yQ and yP, duplicate yP
        lambda_different_points += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute yQ - yP
        lambda_different_points += Script.parse_string("OP_2ROT")  # Bring lambda * (x_P - x_Q)
        lambda_different_points += fq2.add(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda * (x_P - x_Q) + yQ- yP
        lambda_different_points += Script.parse_string("OP_CAT OP_0 OP_EQUALVERIFY")

        # Compute coordinates
        # After this, the stack is: xP lambda x_(P+Q)
        compute_coordinates = Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")  # Put yP on altstack
        compute_coordinates += Script.parse_string("OP_2OVER")  # Duplicate xP
        compute_coordinates += fq2.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute (xP + xQ)
        compute_coordinates += Script.parse_string(
            "OP_2ROT OP_2SWAP OP_2OVER"
        )  # Roll lambda, reorder, duplicate lambda
        compute_coordinates += fq2.square(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda^2
        compute_coordinates += Script.parse_string("OP_2SWAP")
        compute_coordinates += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda^2 - (xP + xQ)

        # After this, the stack is: x_(P+Q) lambda (x_P - x_(P+Q))
        compute_coordinates += Script.parse_string("OP_2ROT OP_2OVER")
        compute_coordinates += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_(P+Q)
        compute_coordinates += Script.parse_string("OP_2ROT")
        compute_coordinates += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda (x_P - x_(P+Q))

        # After this, the stack is: x_(P+Q) y_(P+Q)
        compute_coordinates += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")
        compute_coordinates += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
        )  # y_(P+Q)

        out += lambda_different_points + compute_coordinates

        return out

    def point_doubling(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        position_lambda: int = 5,
        position_p: int = 3,
    ) -> Script:
        """Point doubling.

        Input Parameters:
            - Stack: q .. <lambda> .. P ..
            - Altstack: []
        Output:
            - 2P
        Assumption on parameters:
            - P is a point on E(F_q^2), passed as an element in Fq2
            - lambda is the gradient of the line tangent at P, passed as an element in Fq2
            - P is not the point at infinity --> This function is not able to handle such case
            - position_lambda, position_p denote the positions in the stack (top of stack is position 0)
            of the first element of lambda, P
        Assumption on variables:
            - a is the a coefficient in the Short-Weierstrass equation of the curve (an element in Fq2)
        Assumption on arguments:
            - position_lambda > 0
            - position_p > 0
            - position_lambda > position_p + 1

        If take_modulo = True, the coordinates of 2P are in F_q

        By default, position_lambda = 5 and position_p = 3, which means we assume the stack looks as follows:
        .. <lambda> P
        namely, we assume the stack has been prepared in advance.
        """
        assert position_lambda > 0, f"Position lambda {position_lambda} must be bigger than 0"
        assert position_p > 0, f"Position Q {position_p} must be bigger than 0"
        assert (
            position_lambda - position_p > 1
        ), f"Position lambda {position_lambda} must be bigger than position P {position_p} plus one"

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

        # P \neq Q, then check that 2 lambda y_P = 3 x_P^2 + a
        # At the end of this part, the stack is: lambda yP xP

        # After this, the stack is: lambda yP lambda yP
        stack_length_added = 0
        lambda_equal_points = roll(position=position_lambda, n_elements=2)  # Roll lambda
        stack_length_added += 2
        lambda_equal_points += roll(position=position_p + stack_length_added - 2, n_elements=2)  # Roll yP
        stack_length_added += 0  # Elements were already in front of xP
        lambda_equal_points += Script.parse_string("OP_2OVER OP_2OVER")  # Duplicate lambda, yP
        stack_length_added += 4
        # After this, the stack is: lambda yP (2*lambda*yP)
        lambda_equal_points += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lamdba * yP
        stack_length_added -= 2
        lambda_equal_points += Script.parse_string("OP_2")
        lambda_equal_points += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute 2 * lamdba * yP
        # After this, the stack is: lambda yP xP
        lambda_equal_points += roll(position=position_p + stack_length_added, n_elements=2)  # Roll xP
        lambda_equal_points += Script.parse_string("OP_2SWAP OP_2OVER")
        lambda_equal_points += fq2.square(take_modulo=False, check_constant=False, clean_constant=False)  # Compute xP^2
        lambda_equal_points += Script.parse_string("OP_3")
        lambda_equal_points += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute 3 * xP^2
        if any(curve_a):
            lambda_equal_points += nums_to_script(curve_a)
            lambda_equal_points += fq2.add(
                take_modulo=False, check_constant=False, clean_constant=False
            )  # Compute 3 x_P^2 + a if a != 0
        lambda_equal_points += fq2.subtract(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )
        lambda_equal_points += Script.parse_string("OP_CAT OP_0 OP_EQUALVERIFY")

        # Compute coordinates
        # After this, the stack is: yP lambda xP x_(2P)
        compute_coordinates = Script.parse_string("OP_2ROT OP_2DUP")  # Roll lambda and duplicate it
        compute_coordinates += fq2.square(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda^2
        compute_coordinates += Script.parse_string("OP_2ROT OP_2SWAP OP_2OVER")  # Roll xP and duplicate it
        compute_coordinates += Script.parse_string("OP_2")
        compute_coordinates += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute 2 * xP
        compute_coordinates += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda^2 - 2*xP

        # After this, the stack is: yP x_(2P) lambda * (xP - x_(2P))
        compute_coordinates += Script.parse_string("OP_2SWAP OP_2OVER")
        compute_coordinates += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_(2P)
        compute_coordinates += Script.parse_string("OP_2ROT")
        compute_coordinates += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda * (xP - x_(2P))

        # After this, the stack is: x_(2P) y_(2P)
        compute_coordinates += Script.parse_string("OP_2ROT")
        compute_coordinates += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
        )  # Compute y_(2P)

        out += lambda_equal_points + compute_coordinates

        return out

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

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # Check if P is point at infinity
        out += Script.parse_string("OP_2OVER OP_2OVER")
        out += Script.parse_string("OP_CAT OP_CAT OP_CAT 0x00000000 OP_EQUAL OP_NOT OP_IF")

        # If not, carry out the negation
        out += fq2.negate(take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False)

        if take_modulo:
            assert is_constant_reused is not None
            # After this, the stack is: P.x0, altstack = [-P.y, P.x1]
            out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK OP_TOALTSTACK")

            fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

            batched_modulo = Script()
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")
            if is_constant_reused:
                batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")
            else:
                batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD")

            out += fetch_q + batched_modulo

        # Else, exit
        out += Script.parse_string("OP_ENDIF")

        return out

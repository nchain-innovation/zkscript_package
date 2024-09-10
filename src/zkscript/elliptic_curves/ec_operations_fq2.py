from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script, pick, roll


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
        self, take_modulo: bool, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Point addition.

        Input Parameters:
            - Stack: q .. <lambda> P Q
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
        If take_modulo = True, the coordinates of P + Q are in Fq2
        """
        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # Fq2 implementation
        fq2 = self.FQ2

        # P \neq Q, then check that lambda (x_P - x_Q) = (y_P - y_Q)
        # After this, the stack is: <lambda> x_P y_P x_Q
        lambda_different_points = pick(position=9, nElements=2)  # Pick lambda
        lambda_different_points += pick(position=9, nElements=2)  # Pick x_P
        lambda_different_points += pick(position=7, nElements=2)  # Pick x_Q
        lambda_different_points += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_Q
        lambda_different_points += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda (x_P - x_Q)
        lambda_different_points += pick(position=7, nElements=2)  # Pick y_P
        lambda_different_points += Script.parse_string("OP_2ROT")  # Roll y_Q
        lambda_different_points += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute y_P - y_Q
        lambda_different_points += fq2.subtract(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda (x_P - x_Q) - (y_P - y_Q)
        lambda_different_points += Script.parse_string("OP_0 OP_EQUALVERIFY OP_0 OP_EQUALVERIFY")

        # Compute x_(P+Q) = lambda^2 - x_P - x_Q
        # After this, the base stack is: <lambda> x_P y_P x_(P+Q)
        compute_x_coordinate = pick(position=7, nElements=2)  # Pick lambda
        compute_x_coordinate += fq2.square(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda^2
        compute_x_coordinate += Script.parse_string("OP_2SWAP")  # Roll x_Q
        compute_x_coordinate += pick(position=7, nElements=2)  # Pick x_P
        compute_x_coordinate += fq2.add(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute (x_P + x_Q)
        compute_x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda^2 - (x_P + x_Q))

        # Compute y_(P+Q) = lambda (x_P - x_(P+Q)) - y_P
        compute_y_coordinate = roll(position=7, nElements=2)  # Roll lambda
        compute_y_coordinate += roll(position=7, nElements=2)  # Roll x_P
        compute_y_coordinate += pick(position=5, nElements=2)  # Pick x_(P+Q)
        compute_y_coordinate += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute (x_P - x_(P+Q))
        compute_y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda (x_P - x_(P+Q))
        compute_y_coordinate += Script.parse_string("OP_2ROT")  # Roll y_P
        compute_y_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
        )  # Compute lambda (x_P - x_(P+Q)) - y_P

        out += lambda_different_points + compute_x_coordinate + compute_y_coordinate

        return out

    def point_doubling(
        self, take_modulo: bool, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Point doubling.

        Input Parameters:
            - Stack: q .. <lambda> P
            - Altstack: []
        Output:
            - 2P
        Assumption on parameters:
            - P is a point on E(F_q^2), passed as an element in Fq2
            - lambda is the gradient of the line tangent at P, passed as an element in Fq2
            - P is not the point at infinity --> This function is not able to handle such case
        Assumption on variables:
            - a is the a coefficient in the Short-Weierstrass equation of the curve (an element in Fq2)
        If take_modulo = True, the coordinates of 2P are in F_q
        """
        # Fq2 implementation
        fq2 = self.FQ2
        # A coefficient
        curve_a = self.CURVE_A

        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # P = Q, then check 2 lambda y_P = 3 x_P^2
        # After this, the base stack is: <lambda> x_P y_P
        lambda_equal_points = Script.parse_string("OP_2DUP")  # Duplicate y_P
        lambda_equal_points += Script.parse_string("OP_2")
        lambda_equal_points += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute 2y_P
        lambda_equal_points += pick(position=7, nElements=2)  # Pick lambda
        lambda_equal_points += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute 2 lambda y_P
        lambda_equal_points += pick(position=5, nElements=2)  # Pick x_P
        lambda_equal_points += fq2.square(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P^2
        lambda_equal_points += Script.parse_string("OP_3")
        lambda_equal_points += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute 3 x_P^2
        if not all([el == 0 for el in curve_a]):
            lambda_equal_points += nums_to_script(curve_a)
            lambda_equal_points += fq2.add(
                take_modulo=False, check_constant=False, clean_constant=False, is_constant_reused=False
            )  # Compute 3 x_P^2 + a if a != 0
        lambda_equal_points += fq2.subtract(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute 2 lambda y_P - 3 x_P^2
        lambda_equal_points += Script.parse_string("OP_0 OP_EQUALVERIFY OP_0 OP_EQUALVERIFY")

        # Compute x_(2P) = lambda^2 - 2 x_P
        # After this, the base stack is: <lambda> x_P y_P x_(2P)
        compute_x_coordinate = pick(position=5, nElements=2)  # Pick lambda
        compute_x_coordinate += fq2.square(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda^2
        compute_x_coordinate += pick(position=5, nElements=2)  # Pick x_P
        compute_x_coordinate += Script.parse_string("OP_2")
        compute_x_coordinate += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute 2 x_P
        compute_x_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda^2 - (2 x_P)

        # Compute y_(2P) = lambda (x_P - x_(2P)) - y_P
        compute_y_coordinate = roll(position=7, nElements=2)  # Roll lambda
        compute_y_coordinate += roll(position=7, nElements=2)  # Roll x_P
        compute_y_coordinate += pick(position=5, nElements=2)  # Pick x_(2P)
        compute_y_coordinate += fq2.subtract(take_modulo=False, check_constant=False, clean_constant=False)
        compute_y_coordinate += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda (x_P - x_(2P))
        compute_y_coordinate += roll(position=5, nElements=2)  # Roll y_P
        compute_y_coordinate += fq2.subtract(
            take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
        )  # Compute lambda (x_P - x_(2P)) - y_P

        out += lambda_equal_points + compute_x_coordinate + compute_y_coordinate

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

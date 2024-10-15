"""ec_operations_fq module.

This module enables constructing Bitcoin scripts that perform elliptic curve arithmetic in E(F_q).
"""

from tx_engine import Script

from src.zkscript.util.utility_scripts import nums_to_script, pick, roll


class EllipticCurveFq:
    """Construct Bitcoin scripts that perform elliptic curve arithmetic in E(F_q).

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

    def point_addition(
        self, take_modulo: bool, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Point addition in E(F_q) for points that are not equal, nor their inverse, not the point at infinity.

        Stack input:
            - stack:    [q, ..., lambda, P := (xP, yP), Q := (xQ, yQ)], `P` and `Q` are points on E(F_q)
            - altstack: []

        Stack output:
            - stack:    [q, ..., P + Q]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to add two points on E(F_q).

        Preconditions:
            - P != Q (otherwise any `lambda` will pass the validity check, but the point returned is not necessarily
            2P).
            - P != -Q.
            - P and Q are not the point at infinity.
            - `lambda` is the gradient of the line through `P` and `Q`.
        """
        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        # P \neq Q, then check that lambda (x_Q - x_P) = (y_Q - y_P)
        # After this, the stack is: x_P y_P x_Q lambda, altstack = [(lambda *(xP - xQ) - (yP - yQ) == 0)]
        lambda_different_points = Script.parse_string("OP_2OVER")  # Duplicate xP yP
        lambda_different_points += Script.parse_string("OP_ROT OP_SUB OP_TOALTSTACK")  # Compute yP - yQ
        lambda_different_points += Script.parse_string("OP_OVER OP_SUB")  # Compute xP - xQ
        lambda_different_points += roll(position=4, n_elements=1)  # Roll lambda
        lambda_different_points += Script.parse_string("OP_TUCK OP_MUL")  # Compute lambda *(xP - xQ)
        lambda_different_points += Script.parse_string(
            "OP_FROMALTSTACK OP_SUB"
        )  # Compute lambda *(xP - xQ) - (yP - yQ)
        lambda_different_points += Script.parse_string("OP_TOALTSTACK")

        # Compute x_(P+Q) = lambda^2 - x_P - x_Q
        # After this, the stack is: lambda xP x_(P+Q), altstack = [(lambda *(xP - xQ) - (yP - yQ) == 0), yP]
        compute_coordinates = Script.parse_string("OP_DUP OP_DUP OP_MUL")  # Duplicate lambda and compute lambda^2
        compute_coordinates += Script.parse_string("OP_ROT OP_SUB")  # Rotate xQ and compute lambda^2 - xQ
        compute_coordinates += Script.parse_string(
            "OP_2SWAP OP_TOALTSTACK OP_TUCK"
        )  # Swap xP yP, place yP on altstack, duplicate xP
        compute_coordinates += Script.parse_string("OP_SUB")  # Compute lambda^2 - xP - xQ

        # Compute y_(P+Q)
        compute_coordinates += Script.parse_string("OP_TUCK OP_SUB")  # Compute xP - x_(P+Q)
        compute_coordinates += Script.parse_string("OP_ROT OP_MUL")  # Compute lambda * (xP - x_(P+Q))
        compute_coordinates += Script.parse_string("OP_FROMALTSTACK OP_SUB")  # Compute y_(P+Q)

        if clean_constant:
            fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
        else:
            fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

        # After this, the stack is: x_(P+Q) y_(P+Q) q, altstack = [(lambda *(xP - xQ) - (yP - yQ) == 0)]
        out += lambda_different_points + compute_coordinates + fetch_q

        batched_modulo = Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")  # Mod out y
        batched_modulo += Script.parse_string("OP_TOALTSTACK")
        batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")  # Mod out x
        batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")

        # If needed, mod out
        # After this, the stack is: x_(P+Q) y_(P+Q) q, altstack = [(lambda *(xP - xQ) - (yP - yQ) == 0)]
        # with the coefficients in Fq (if executed)
        if take_modulo:
            out += batched_modulo

        check_lambda = Script.parse_string("OP_FROMALTSTACK")
        check_lambda += Script.parse_string(
            "OP_OVER OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD"
        )  # Mod out lambda *(xP - xQ) - (yP - yQ)
        check_lambda += Script.parse_string("OP_0 OP_EQUALVERIFY")

        # Check lambda was correct
        out += check_lambda

        return out

    def point_doubling(
        self, take_modulo: bool, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Point doubling in E(F_q).

        Stack input:
            - stack:    [q, ..., lambda, P := (xP, yP)], `P` is a point on E(F_q)
            - altstack: []

        Stack output:
            - stack:    [q, ..., 2P]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to double a point on E(F_q).

        Preconditions:
            - `lambda` is the gradient of the line tangent at `P`.
        """
        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

        curve_a = self.CURVE_A

        # P = Q, then check 2 lambda y_P = 3 x_P^2
        # After this, the stack is: xP yP lambda, altstack = [2*lambda*yP - 3*xP^2]
        lambda_equal_points = Script.parse_string("OP_ROT OP_2DUP")  # Rotate lambda and duplicate lambda, yP
        lambda_equal_points += Script.parse_string("OP_2 OP_MUL OP_MUL")  # Compute 2 lambda yP
        lambda_equal_points += pick(position=3, n_elements=1)  # Pick xP
        lambda_equal_points += Script.parse_string("OP_DUP OP_3 OP_MUL OP_MUL")  # Compute 3xP^2
        if curve_a != 0:
            lambda_equal_points += nums_to_script([curve_a]) + Script.parse_string("OP_ADD")
        lambda_equal_points += Script.parse_string("OP_SUB")
        lambda_equal_points += Script.parse_string("OP_TOALTSTACK")

        # Compute coodinates
        # After this, the stack is: yP lambda xP x_(2P)
        compute_coordinates = Script.parse_string("OP_ROT OP_OVER")  # Rotate xP, duplicate lambda
        compute_coordinates += Script.parse_string("OP_DUP OP_MUL")  # Compute lambda^2
        compute_coordinates += Script.parse_string("OP_OVER")  # Roll xP
        compute_coordinates += Script.parse_string("OP_2 OP_MUL")  # Compute 2xP
        compute_coordinates += Script.parse_string("OP_SUB")  # Compute x_(2P)

        # After this, the stack is: x_(2P) y_(2P)
        compute_coordinates += Script.parse_string("OP_TUCK")  # Duplicate x_(2P)
        compute_coordinates += Script.parse_string("OP_SUB")  # Compute xP - x_(2P)
        compute_coordinates += Script.parse_string("OP_ROT")  # Roll lambda
        compute_coordinates += Script.parse_string("OP_MUL")  # Compute lambda * (xP - x_(2P))
        compute_coordinates += Script.parse_string("OP_ROT")  # Roll lambda
        compute_coordinates += Script.parse_string("OP_SUB")  # Compute lambda * (xP - x_(2P))

        if clean_constant:
            fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_ROLL")
        else:
            fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

        # After this, the stack is: x_(P+Q) y_(P+Q) q, altstack = [lambda * 2yP == 3xP^2]
        out += lambda_equal_points + compute_coordinates + fetch_q

        batched_modulo = Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")  # Mod out y
        batched_modulo += Script.parse_string("OP_TOALTSTACK")
        batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")  # Mod out x
        batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")

        # If needed, mod out
        # After this, the stack is: x_(P+Q) y_(P+Q) q, altstack = [lambda * 2yP == 3xP^2]
        # with the coefficients in Fq (if executed)
        if take_modulo:
            out += batched_modulo

        check_lambda = Script.parse_string("OP_FROMALTSTACK")
        check_lambda += Script.parse_string(
            "OP_OVER OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD"
        )  # Mod out lambda * (yP - yQ) - (xP- xQ)
        check_lambda += Script.parse_string("OP_0 OP_EQUALVERIFY")

        # Check lambda was correct
        out += check_lambda

        return out

    def point_addition_with_unknown_points(
        self, take_modulo: bool, check_constant: bool | None = None, clean_constant: bool | None = None
    ) -> Script:
        """Point addition in E(F_q) for points that may be equal, or their inverse, or the point at infinity.

        Stack input:
            - stack:    [q, ..., lambda, P := (xP, yP), Q := (xQ, yQ)], `P` and `Q` are points on E(F_q), `lambda` is an
                optional integer
            - altstack: []

        Stack output:
            - stack:    [q, ..., P + Q]
            - altstack: []

        Args:
            take_modulo (bool): If `True`, the result is reduced modulo `q`.
            check_constant (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constant (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.

        Returns:
            Script to add two points on E(F_q). If P = -Q, the point at infinity (0x00, 0x00) is returned.

        Preconditions:
            - If P != -Q, then `lambda` is the gradient of the line through `P` and `Q`.
            - If P = -Q, or `P` is the point at infinity, or `Q` is the point at infinity, then `lambda` should not
            be on the stack.

        Notes:
            The point at infinity (0x00, 0x00) is a data payload, not a couple of integers. Points are assumed to be
            passed as a couple of integers. E.g. (0, 0) would have to be passed as OP_0 OP_0.
        """
        if check_constant:
            out = (
                Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
                + nums_to_script([self.MODULUS])
                + Script.parse_string("OP_EQUALVERIFY")
            )
        else:
            out = Script()

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

        fetch_q = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")

        # After this, the stack is: (P+Q) q, altstack = [Verify(lambda)]
        out += compute_x_coordinate + compute_y_coordinate + fetch_q

        batched_modulo = Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")  # Mod y
        batched_modulo += Script.parse_string("OP_TOALTSTACK")
        batched_modulo += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")  # Mod x
        batched_modulo += Script.parse_string("OP_FROMALTSTACK OP_ROT")

        # If needed, mod out
        # After this, the stack is: (P+Q) q, altstack = [Verify(lambda)] with the coefficients in Fq (if executed)
        if take_modulo:
            out += batched_modulo

        check_lambda = Script.parse_string("OP_FROMALTSTACK")
        check_lambda += Script.parse_string(
            "OP_OVER OP_MOD OP_OVER OP_ADD OP_SWAP OP_MOD"
        )  # Mod lambda * (yP - yQ) - (xP- xQ)
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

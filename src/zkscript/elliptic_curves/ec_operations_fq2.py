from tx_engine import Script

from src.zkscript.elliptic_curves.util import CurvePoint, FieldElement
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

    def point_algebraic_addition(
        self,
        take_modulo: bool,
        check_constant: bool | None,
        clean_constant: bool | None,
        lam: FieldElement | None = None,
        P: CurvePoint | None = None,  # noqa: N803
        Q: CurvePoint | None = None,  # noqa: N803
    ) -> Script:
        """Point algebraic addition.

        NOTE: use this function only if P != Q and P != -Q, and neither is the point at infinity
        Input Parameters:
            - Stack: q .. <lambda> .. P .. Q ..
            - Altstack: []
        Output:
            - q .. <lambda> .. P .. .. P + Q if P.move = pick and neither P nor Q is negated
            - q .. <lambda> .. P .. .. P - Q if P.move = pick and Q is negated
            - q .. <lambda> .. P .. .. -P + Q if P.move = pick and P is negated
            - q .. <lambda> .. P .. .. - P - Q if P.move = pick and P and Q are negated
            - q .. .. .. .. P + Q if P.move = roll and neither P nor Q is negated
            - q .. .. .. .. P - Q if P.move = roll and Q is negated
            - q .. .. .. .. -P + Q if P.move = roll and P is negated
            - q .. .. .. .. - P - Q if P.move = roll and P and Q are negated
        Assumption on parameters:
            - P and Q are points on E(F_q^2), passed as couple of elements of Fq2
            - lambda is the gradient of the line through P and Q, passed as an element in Fq2
            - P != Q
            - P != -Q
            - P and Q are not the point at infinity --> This function is not able to handle such case
            - position_lambda, position_p and position_q denote the positions in the stack (top of stack is position 1)
            of the first element of lambda, P, and Q respectively
        Assumption on arguments:
            - position_lambda, position_p, position_q > 0
            - position_lambda > position_p + 1, position_p > position_q + 3

        If take_modulo = True, the coordinates of P + Q are in Fq2.

        By default:
            - lam = FieldElement(9,roll)
            - P = CurvePoint(7,False,roll)
            - Q = CurvePoint(3,False,roll)
        which means we assume the stack looks as follows (and that P and Q don't need to be negated):
        .. <lambda> P Q
        namely, we assume the stack has been prepared in advance.
        """
        if lam is None:
            lam = FieldElement(9, roll)
        if P is None:
            P = CurvePoint(7, False, roll)
        if Q is None:
            Q = CurvePoint(3, False, roll)

        assert lam.position > 0, f"Position lambda {lam.position} must be bigger than 0"
        assert P.position > 0, f"Position P {P.position} must be bigger than 0"
        assert Q.position > 0, f"Position Q {Q.position} must be bigger than 0"
        assert (
            lam.position - P.position > 1
        ), f"Position lambda {lam.position} must be bigger than position P {P.position} plus one"
        assert (
            P.position - Q.position > 3  # noqa: PLR2004
        ), f"Position P {P.position} must be bigger than position Q {Q.position} plus three"
        assert lam.move == roll, "The moving function for lambda must be rollin"
        assert Q.move == roll, "The moving function for Q must be rolling"

        if check_constant:
            out = Script.parse_string("OP_DEPTH OP_1SUB OP_PICK")
            out += nums_to_script([self.MODULUS])
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out = Script()

        # Fq2 implementation
        fq2 = self.FQ2

        # Checks consistency of P, Q, and lambda. The notation [P / yP] means that we have either P or yP in the stack
        # After this, the stack is: q .. .. [P / yP] .. Q ..

        # lambda xP lambda xP
        lambda_different_points = lam.move(position=lam.position, n_elements=2)  # Roll lambda
        lambda_different_points += P.move(position=P.position + 2, n_elements=2)  # Move xP
        lambda_different_points += Script.parse_string("OP_2OVER OP_2OVER")  # Duplicate lambda, xP
        # After this, the stack is: q .. .. [P / yP] .. yQ ..
        # lambda xP xQ [lambda * (xP - xQ)]
        lambda_different_points += Q.move(position=Q.position + 8, n_elements=2)  # Roll xQ
        lambda_different_points += Script.parse_string("OP_2SWAP OP_2OVER")  # Swap xP and xQ, duplicate xQ
        lambda_different_points += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute x_P - x_Q
        lambda_different_points += Script.parse_string("OP_2ROT")  # Bring lambda on top of the stack
        lambda_different_points += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lambda * (x_P - x_Q)
        # After this, the stack is: q .. .. [P / ""] .. ..
        # lambda xP xQ (\pm yP)
        # Dealing with different combination of P, Q, -P, and -Q
        lambda_different_points += Q.move(position=Q.position + 8 - 2, n_elements=1)  # Roll yQ_0
        if Q.negate:
            lambda_different_points += Script.parse_string("OP_NEGATE")
        lambda_different_points += Q.move(position=Q.position + 8 - 3 + 1, n_elements=1)  # Roll yQ_1
        if Q.negate:
            lambda_different_points += Script.parse_string("OP_NEGATE")
        lambda_different_points += P.move(position=P.position - 2 + 6, n_elements=1)  # Move yP_0
        if P.negate:
            lambda_different_points += Script.parse_string("OP_NEGATE")
        lambda_different_points += P.move(position=P.position - 3 + 6 + 1, n_elements=1)  # Roll yP_1
        if P.negate:
            lambda_different_points += Script.parse_string("OP_NEGATE")
        lambda_different_points += Script.parse_string(
            "OP_2SWAP OP_2OVER"
        )  # Swap (\pm yQ) and (\pm yP), duplicate (\pm  yP)
        lambda_different_points += fq2.subtract(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute (\pm yQ) - (\pm yP)
        lambda_different_points += Script.parse_string("OP_2ROT")  # Bring lambda * (x_P - x_Q)
        lambda_different_points += fq2.add(
            take_modulo=True, check_constant=False, clean_constant=False, is_constant_reused=False
        )  # Compute lambda * (x_P - x_Q) + (\pm yQ - \pm yP)

        lambda_different_points += Script.parse_string("OP_CAT OP_0 OP_EQUALVERIFY")

        # Compute coordinates
        # After this, the stack is: xP lambda x_(P+Q)
        compute_coordinates = Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")  # Put (\pm yP) on altstack
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
        lam: FieldElement | None = None,
        P: CurvePoint | None = None,  # noqa: N803
    ) -> Script:
        """Point doubling.

        Input Parameters:
            - Stack: q .. <lambda> .. P ..
            - Altstack: []
        Output:
            - q .. .. P .. 2P if P.move == pick and P.negate = False
            - q .. .. .. 2P if P.move == roll and P.negate = False
            - q .. .. P .. -2P if P.move == pick and P.negate = True
            - q .. .. .. -2P if P.move == roll and P.negate = True
        Assumption on parameters:
            - P is a point on E(F_q^2), passed as an element in Fq2
            - lambda is the gradient of the line tangent at P, passed as an element in Fq2
            - P is not the point at infinity --> This function is not able to handle such case
            - position_lambda, position_p denote the positions in the stack (top of stack is position 0)
            of the first element of lambda, P
        Assumption on variables:
            - a is the a coefficient in the Short-Weierstrass equation of the curve (an element in Fq2)
        Assumption on arguments:
            - lam.position > 0
            - P.position > 0
            - lam.position > P.position + 1

        If take_modulo = True, the coordinates of 2P are in F_q

        By default, lam = FieldElement(5,roll) and P = CurvePoint(3,roll), which means we assume the stack looks like:
        .. <lambda> P
        namely, we assume the stack has been prepared in advance.
        """
        if lam is None:
            lam = FieldElement(5, roll)
        if P is None:
            P = CurvePoint(3, False, roll)

        assert lam.position > 0, f"Position lambda {lam.position} must be bigger than 0"
        assert P.position > 0, f"Position Q {P.position} must be bigger than 0"
        assert (
            lam.position - P.position > 1
        ), f"Position lambda {lam.position} must be bigger than position P {P.position} plus one"
        assert lam.move == roll, "The moving function for lambda must be rolling"

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
        # The notation [P / yP] means that we have either P or yP in the stack
        # After this, the stack is: q .. .. [P / xP] ..
        # lambda yP lambda yP
        lambda_equal_points = lam.move(position=lam.position, n_elements=2)  # Roll lambda
        lambda_equal_points += P.move(position=P.position + 2 - 2, n_elements=2)  # Move yP
        lambda_equal_points += Script.parse_string("OP_2OVER OP_2OVER")  # Duplicate lambda, yP
        # After this, the stack is:q .. .. [P / xP] ..
        # lambda yP (2*lambda*yP)
        lambda_equal_points += fq2.mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute lamdba * yP
        lambda_equal_points += Script.parse_string("OP_2")
        if P.negate:
            lambda_equal_points += Script.parse_string("OP_NEGATE")
        lambda_equal_points += fq2.scalar_mul(
            take_modulo=False, check_constant=False, clean_constant=False
        )  # Compute 2 * lamdba * yP
        # After this, the stack is: q .. .. [P / ""] ..
        # lambda yP xP
        lambda_equal_points += P.move(position=P.position + 4 + 2 * (P.move == pick), n_elements=2)  # Move xP
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
        if P.negate:
            compute_coordinates += fq2.add(
                take_modulo=take_modulo, check_constant=False, clean_constant=clean_constant, is_constant_reused=False
            )  # Compute y_(2P)
        else:
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

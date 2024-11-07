from tx_engine import Script
from tx_engine.engine.util import GROUP_ORDER_INT, PRIME_INT, Gx, Gx_bytes, Gy

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.elliptic_curves.secp256k1.util import (
    int_sig_to_s_component,
    stack_elliptic_curve_point_to_compressed_pubkey,
    x_coordinate_to_r_component,
)
from src.zkscript.types.stack_elements import (
    StackBaseElement,
    StackEllipticCurvePoint,
    StackFiniteFieldElement,
    StackNumber,
)
from src.zkscript.util.utility_functions import (
    bitmask_to_boolean_list,
    bool_to_moving_function,
    boolean_list_to_bitmask,
    check_order,
)
from src.zkscript.util.utility_scripts import mod, move, nums_to_script, pick, reverse_endianness, roll


class Secp256k1:
    GROUP_ORDER = GROUP_ORDER_INT
    Gx = Gx
    Gy = Gy
    Gx_bytes = Gx_bytes
    MODULUS = PRIME_INT
    ec_fq = EllipticCurveFq(MODULUS, 0)

    @classmethod
    def verify_base_point_multiplication_up_to_epsilon(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        additional_constant: int = 0,
        h: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        a: StackFiniteFieldElement = StackFiniteFieldElement(1, False, 1),  # noqa: B008
        A: StackBaseElement | StackEllipticCurvePoint = StackBaseElement(0),  # noqa: B008, N803
        rolling_options: int = 7,
    ) -> Script:
        r"""Verify that A = (\pm a + additional_constant + epsilon)G.

        This script verifies that A = (\pm a + additional_constant + epsilon)G, where:
        - A is a point on E
        - a is a scalar
        - G is the generator of secp256k1.

        Stack input:
            - stack:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02||02, .., h .., a .., A]
            - altstack: []
        Stack out:
            - stack:    [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 .., h .., a .., A] or fail
            - altstack: []

        """
        check_order([h, a, A])
        is_h_rolled, is_a_rolled, is_A_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = Script()

        if check_constants:
            out.append_pushdata(bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"))
            out += nums_to_script([cls.Gx, cls.GROUP_ORDER])
            out += pick(position=-1, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-2, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-3, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")

        # Compute h + a
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02||02, .., h, .., a, .., A, ..,]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02||02, .., h, .., a, .., A, ..,
        #               0x0220||Gx_bytes||02||02 GROUP_ORDER (h + a*Gx)]
        out += (
            roll(position=-3, n_elements=1) if clean_constants else pick(position=-3, n_elements=1)
        )  # Move 0x0220||Gx_bytes||02||02
        out += move(a.shift(1), bool_to_moving_function(is_a_rolled))  # Move a
        if a.negate:
            out += Script.parse_string("OP_NEGATE")
        if additional_constant:
            out += (
                Script.parse_string("OP_1ADD")
                if additional_constant == 1
                else Script.parse_string("OP_1SUB")
                if additional_constant == -1
                else nums_to_script([additional_constant]) + Script.parse_string("OP_ADD")
            )
        out += roll(position=-2, n_elements=1) if clean_constants else pick(position=-2, n_elements=1)  # Move Gx
        out += Script.parse_string("OP_MUL")  # Compute a*Gx
        out += move(h.shift(2 - 1 * is_a_rolled), bool_to_moving_function(is_h_rolled))  # Move h
        out += Script.parse_string("OP_ADD")
        out += (
            roll(position=-1, n_elements=1) if clean_constants else pick(position=-1, n_elements=1)
        )  # Move GROUP_ORDER
        out += mod(stack_preparation="")  # Compute (h+a*Gx) % GROUP_ORDER

        # Convert (h + a*Gx) to s-component of the signature
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02||02, .., h, .., a, .., A, ..,
        #               0x0220||Gx_bytes||02||02 GROUP_ORDER (h + a*Gx)]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02||02, .., h, .., a, .., A, ..,
        #               0x0220||Gx_bytes||02||02, s]
        out += int_sig_to_s_component(add_prefix=False)

        # Compute the signature
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02||02, .., h, .., a, .., A, ..,
        #               0x0220||Gx_bytes||02||02 s]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02||02, .., h, .., a, .., A, ..,
        #               Der(Gx,s)]
        out += Script.parse_string(
            "OP_SIZE OP_TUCK OP_TOALTSTACK OP_CAT OP_CAT"
        )  # Construct 0x0220||Gx||02||len(s)||s and put len(s) on the altstack
        out += Script.parse_string("0x30 OP_FROMALTSTACK")
        out += nums_to_script([36])
        out += Script.parse_string("OP_ADD OP_CAT OP_SWAP OP_CAT")  # Construct DER(Gx,s)
        out += Script.parse_string("0x41 OP_CAT")  # Append SIGHASH_ALL

        # Enforce Der(Gx,s) A OP_CHECKSIG
        if isinstance(A, StackEllipticCurvePoint):
            out += stack_elliptic_curve_point_to_compressed_pubkey(
                A.shift(1), is_A_rolled
            )  # Convert A to compressed public key
        elif isinstance(A, StackBaseElement):
            out += move(A.shift(1), bool_to_moving_function(is_A_rolled))  # Move A
        else:
            msg = "Type not supported for A: type(A): type(A)"
            raise ValueError(msg)

        out += Script.parse_string("OP_CHECKSIGVERIFY")

        return out

    @classmethod
    def verify_base_point_multiplication_with_addition(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        h: StackFiniteFieldElement = StackFiniteFieldElement(4, False, 1),  # noqa: B008
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(3, False, 1),  # noqa: B008
        a: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        A: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 15,
    ) -> Script:
        """Verify that A = aG.

        This script verifies that A = aG, where:
        - A is a point on E
        - a is a scalar
        - G is the generator of secp256k1.

        Stack input:
            - stack: PRIME_INT GROUP_ORDER Gx 0x0220||Gx_bytes||02, Gy, MODULUS, .., h .., gradient .., a .., A, ..,
            - altstack:
        Stack out:
            - stack: GROUP_ORDER Gx 0x0220||Gx_bytes||02, Gy, .., h .., gradient .., a .., A, ..,,
            or fail
            - altstack:

        """

        check_order([h, gradient, a, A])
        is_h_rolled, is_gradient_rolled, is_a_rolled, is_A_rolled = bitmask_to_boolean_list(rolling_options, 4)

        out = Script()

        if check_constants:
            out += nums_to_script(
                [
                    cls.Gy,
                ]
            )
            out.append_pushdata(bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"))
            out += nums_to_script(
                [
                    cls.Gx,
                    cls.GROUP_ORDER,
                    cls.MODULUS,
                ]
            )
            out += pick(position=-1, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-2, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-3, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-4, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-5, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")

        # Compute A + G
        # stack in:  [PRIME_INT GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 Gy, .., h .., gradient .., a .., A, ..]
        # stack out: [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 Gy, .., h .., gradient .., a .., A, .., (A + G)]
        out += pick(position=-3, n_elements=1)  # Pick Gx
        out += roll(position=-5, n_elements=1) if clean_constants else pick(position=-5, n_elements=1)  # Move Gy,
        out += cls.ec_fq.point_algebraic_addition(
            take_modulo=True,
            check_constant=False,
            clean_constant=True,
            verify_gradient=True,
            gradient=gradient.shift(2),
            P=A.shift(2),
            rolling_options=boolean_list_to_bitmask([is_gradient_rolled, False, True]),
        )

        # Verify that A = (a + epsilon)G
        # stack in:  [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 Gy, .., h .., gradient .., a .., A, .., (A + G)]
        # stack out: [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 Gy, .., h .., gradient .., a .., A, ..,
        #               (A + G)] or fail
        out += cls.verify_base_point_multiplication_up_to_epsilon(
            check_constants=False,
            clean_constants=False,
            additional_constant=0,
            h=h.shift(2 - 1 * is_gradient_rolled),
            a=a.shift(2),
            A=A.shift(2),
            rolling_options=boolean_list_to_bitmask([False, False, is_A_rolled]),
        )

        # Verify that (A+G) = (a + 1 + epsilon)G
        # stack in:  [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 Gy, .., h .., gradient .., a .., A, ..,
        #               (A + G)]
        # stack out: [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 Gy, .., h .., gradient .., a .., A,
        #               ..] or fail
        out += cls.verify_base_point_multiplication_up_to_epsilon(
            check_constants=False,
            clean_constants=clean_constants,
            additional_constant=1,
            h=h.shift(2 - 2 * is_A_rolled - 1 * is_gradient_rolled),
            a=a.shift(2 - 2 * is_A_rolled),
            A=StackEllipticCurvePoint(StackFiniteFieldElement(1, False, 1), StackFiniteFieldElement(0, False, 1)),
            rolling_options=boolean_list_to_bitmask([is_h_rolled, is_a_rolled, True]),
        )

        return out

    @classmethod
    def verify_base_point_multiplication_with_negation(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        h: StackFiniteFieldElement = StackFiniteFieldElement(3, False, 1),  # noqa: B008
        a: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        A: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 7,
    ) -> Script:
        """Verify that A = aG.

        This script verifies that A = aG, where:
        - A is a point on E
        - a is a scalar
        - G is the generator of secp256k1.

        Stack input:
            - stack: GROUP_ORDER Gx 0x0220||Gx_bytes||02, .., h .., a .., A, ..,
            - altstack:
        Stack out:
            - stack: GROUP_ORDER Gx 0x0220||Gx_bytes||02, .., h .., a .., A, ..,,
            or fail
            - altstack:

        """

        check_order([h, a, A])
        is_h_rolled, is_a_rolled, is_A_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = Script()

        if check_constants:
            out.append_pushdata(bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"))
            out += nums_to_script([cls.Gx, cls.GROUP_ORDER])
            out += pick(position=-1, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-2, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-3, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")

        # Prepare A and -A
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., A, ..]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., A, .., [2/3], A.x, -A]
        out += move(A, bool_to_moving_function(is_A_rolled))
        out += Script.parse_string("OP_2 OP_MOD OP_IF OP_3 OP_2 OP_ELSE OP_2 OP_3 OP_ENDIF")  # Compute A.y % 2
        out += Script.parse_string(
            "OP_ROT 33 OP_NUM2BIN 32 OP_SPLIT OP_DROP"
        )  # Move A.x on top of the stack and make it 32 bytes
        out += reverse_endianness(32)  # Reverse endianness of A.x
        out += Script.parse_string("OP_TUCK OP_CAT")  # Construct -A

        # Verify that -A = (-a + epsilon)G
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., A, .., [2/3], A.x, -A]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., A, .., [2/3], A.x], or fail
        out += cls.verify_base_point_multiplication_up_to_epsilon(
            check_constants=False,
            clean_constants=False,
            additional_constant=0,
            h=h.shift(3 - 2 * is_A_rolled),
            a=a.shift(3 - 2 * is_A_rolled).set_negate(True),
            rolling_options=boolean_list_to_bitmask([False, False, True]),
        )

        # Verify that A = (a + epsilon)G
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., A, ..,
        #               [2/3], A.x]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., A, ..]
        out += Script.parse_string("OP_CAT")  # Construct A
        out += cls.verify_base_point_multiplication_up_to_epsilon(
            check_constants=False,
            clean_constants=clean_constants,
            additional_constant=0,
            h=h.shift(1 - 2 * is_A_rolled),
            a=a.shift(1 - 2 * is_A_rolled),
            rolling_options=boolean_list_to_bitmask([is_h_rolled, is_a_rolled, True]),
        )

        return out

    @classmethod
    def verify_point_multiplication_up_to_sign(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        h: StackFiniteFieldElement = StackFiniteFieldElement(10, False, 1),  # noqa: B008
        b: StackFiniteFieldElement = StackFiniteFieldElement(9, False, 1),  # noqa: B008
        x_coordinate_target_times_b_inverse: StackFiniteFieldElement = StackFiniteFieldElement(8, False, 1),  # noqa: B008
        h_times_x_coordinate_target_inverse: StackFiniteFieldElement = StackFiniteFieldElement(7, False, 1),  # noqa: B008
        gradient: StackFiniteFieldElement = StackFiniteFieldElement(6, False, 1),  # noqa: B008
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(5, False, 1),  # noqa: B008
            StackFiniteFieldElement(4, False, 1),  # noqa: B008
        ),
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(3, False, 1),  # noqa: B008
            StackFiniteFieldElement(2, False, 1),  # noqa: B008
        ),
        h_times_x_coordinate_target_inverse_times_G: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = 511,
    ) -> Script:
        """Verify Q = ± b * P.

        Stack input:
            - stack: [MODULUS, GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
                        x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient, ..,
                            Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..]
        """

        check_order(
            [
                h,
                b,
                x_coordinate_target_times_b_inverse,
                h_times_x_coordinate_target_inverse,
                gradient,
                Q,
                P,
                h_times_x_coordinate_target_inverse_times_G,
            ]
        )
        list_rolling_options = bitmask_to_boolean_list(rolling_options, 8)

        out = Script()

        if check_constants:
            out.append_pushdata(bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"))
            out += nums_to_script([cls.Gx, cls.GROUP_ORDER, cls.MODULUS])
            out += pick(position=-1, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-2, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-3, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")
            out += pick(position=-4, n_elements=1)
            out += Script.parse_string("OP_EQUALVERIFY")

        # Compute P - h_times_x_coordinate_target_inverse_times_G
        # stack in:     [MODULUS, GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient,
        #                       .., Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..]
        # stack out:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient,
        #                       .., Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..]
        # altstack out: [(P - h_times_x_coordinate_target_inverse_times_G)]
        out += cls.ec_fq.point_algebraic_addition(
            take_modulo=True,
            check_constant=False,
            clean_constant=True,
            verify_gradient=True,
            gradient=gradient,
            P=P,
            Q=h_times_x_coordinate_target_inverse_times_G.set_negate(True),
            rolling_options=boolean_list_to_bitmask([list_rolling_options[4], list_rolling_options[6], False]),
        )
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Verify x_coordinate_target_times_b_inverse * b = Q.x mod GROUP_ORDER
        # stack in:     [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient,
        #                       .., Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..]
        # altstack in:  [(P - h_times_x_coordinate_target_inverse_times_G)]
        # stack out:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient,
        #                       .., Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, .., Q.x, GROUP_ORDER]
        # altstack out: [(P - h_times_x_coordinate_target_inverse_times_G), x_coordinate_target_times_b_inverse, Q.x]
        out += move(
            x_coordinate_target_times_b_inverse.shift(-list_rolling_options[4] - 2 * list_rolling_options[6]),
            bool_to_moving_function(list_rolling_options[2]),
        )  # Move x_coordinate_target_times_b_inverse
        out += Script.parse_string("OP_DUP OP_TOALTSTACK")
        out += move(
            b.shift(-list_rolling_options[2] - list_rolling_options[4] - 2 * list_rolling_options[6] + 1),
            bool_to_moving_function(list_rolling_options[1]),
        )  # Move b
        out += Script.parse_string("OP_MUL")  # Compute x_coordinate_target_times_b_inverse * b
        out += move(
            Q.x.shift(-2 * list_rolling_options[6] + 1), bool_to_moving_function(list_rolling_options[5])
        )  # Move Q.x
        out += Script.parse_string(
            "OP_DUP OP_TOALTSTACK OP_TUCK OP_SUB"
        )  # Duplicate Q.x, put it on altstack, compute x_coordinate_target_times_b_inverse * b - Q.x
        out += pick(position=-1, n_elements=1)  # Bring GROUP_ORDER on top
        out += mod(stack_preparation="")
        out += Script.parse_string("OP_0 OP_EQUALVERIFY")

        # Verify h_times_x_coordinate_target_inverse * Q.x = h mod GROUP_ORDER
        # stack in:     [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient,
        #                       .., Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, .., Q.x, GROUP_ORDER]
        # altstack in:  [(P - h_times_x_coordinate_target_inverse_times_G), x_coordinate_target_times_b_inverse, Q.x]
        # stack out:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient,
        #                       .., Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..]
        # altstack out: [(P - h_times_x_coordinate_target_inverse_times_G), x_coordinate_target_times_b_inverse, Q.x]
        out += Script.parse_string("OP_SWAP")
        out += move(
            h.shift(
                -list_rolling_options[1]
                - list_rolling_options[2]
                - list_rolling_options[4]
                - list_rolling_options[5]
                - 2 * list_rolling_options[6]
                + 2
            ),
            pick,
        )  # Pick h
        out += move(
            h_times_x_coordinate_target_inverse.shift(
                -list_rolling_options[4] - list_rolling_options[5] - 2 * list_rolling_options[6] + 3
            ),
            pick,
        )  # Pick h_times_x_coordinate_target_inverse
        out += roll(position=2, n_elements=1)  # Bring Q.x on top
        out += Script.parse_string("OP_MUL OP_SUB")  # Compute h_times_x_coordinate_target_inverse * Q.x - h
        out += mod(stack_preparation="", is_mod_on_top=False, is_constant_reused=False)
        out += Script.parse_string(
            "OP_0 OP_EQUALVERIFY"
        )  # Check that h_times_x_coordinate_target_inverse * Q.x - h = 0 mod GROUP_ORDER

        # Convert signature
        # stack in:     [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient,
        #                       .., Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..]
        # altstack in:  [(P - h_times_x_coordinate_target_inverse_times_G), x_coordinate_target_times_b_inverse, Q.x]
        # stack out:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, ..,
        #                       gradient, .., xQ, yP, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..,
        #                           Der(Q.x,x_coordinate_target_times_b_inverse)]
        # altstack out: [(P - h_times_x_coordinate_target_inverse_times_G)]
        out += Script.parse_string("OP_FROMALTSTACK")
        out += x_coordinate_to_r_component()  # Convert Q.x to r-component
        out += Script.parse_string("OP_FROMALTSTACK")
        out += int_sig_to_s_component(
            group_order=StackNumber(-1, False),
            int_sig=StackNumber(0, False),
            rolling_options=boolean_list_to_bitmask([False, True]),
        )  # Convert x_coordinate_target_times_b_inverse to s-component
        out += Script.parse_string(
            "OP_CAT OP_SIZE OP_SWAP OP_CAT 0x30 OP_SWAP OP_CAT 0x41 OP_CAT"
        )  # Construct Der(Q.x,x_coordinate_target_times_b_inverse)

        # Convert (P - h_times_x_coordinate_target_inverse_times_G) to compressed pubkey
        # stack in:     [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, ..,
        #                       gradient, .., xQ, yP, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..,
        #                           Der(Q.x,x_coordinate_target_times_b_inverse)]
        # altstack in:  [(P - h_times_x_coordinate_target_inverse_times_G)]
        # stack out:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, ..,
        #                       gradient, .., xQ, yP, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..,
        #                           Der(Q.x,x_coordinate_target_times_b_inverse),
        #                               compressed(P - h_times_x_coordinate_target_inverse_times_G)]
        # altstack out: []
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")
        out += stack_elliptic_curve_point_to_compressed_pubkey()

        # Verify Der(Q.x,x_coordinate_target_times_b_inverse) is valid signature
        # for compressed(P - h_times_x_coordinate_target_inverse_times_G)
        out += Script.parse_string("OP_CHECKSIGVERIFY")

        # Verify h_times_x_coordinate_target_inverse_times_G = h_times_x_coordinate_target_inverse * G
        # stack in:     [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, ..,
        #                       gradient, .., xQ, yP, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..]
        # altstack in:  []
        # stack out:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, .., b,
        #                   x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient,
        #                       .., Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..] or fail
        # altstack out: []
        out += cls.verify_base_point_multiplication_with_negation(
            check_constants=False,
            clean_constants=clean_constants,
            h=h.shift(
                -list_rolling_options[1]
                - list_rolling_options[2]
                - list_rolling_options[4]
                - list_rolling_options[5]
                - 2 * list_rolling_options[6]
            ),
            a=h_times_x_coordinate_target_inverse.shift(
                -list_rolling_options[4] - list_rolling_options[5] - 2 * list_rolling_options[6]
            ),
            A=h_times_x_coordinate_target_inverse_times_G,
            rolling_options=boolean_list_to_bitmask(
                [list_rolling_options[0], list_rolling_options[3], list_rolling_options[7]]
            ),
        )

        if list_rolling_options[5]:
            out += move(Q.y.shift(-2 * list_rolling_options[6] - 2 * list_rolling_options[7]), roll)
            out += Script.parse_string("OP_DROP")

        return out

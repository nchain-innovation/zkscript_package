from tx_engine import Script
from tx_engine.engine.util import GROUP_ORDER_INT, PRIME_INT, Gx, Gx_bytes, Gy

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.types.stack_elements import StackBaseElement, StackEllipticCurvePoint, StackFiniteFieldElement
from src.zkscript.util.utility_functions import (
    bitmask_to_boolean_list,
    bool_to_moving_function,
    boolean_list_to_bitmask,
    check_order,
)
from src.zkscript.util.utility_scripts import move, nums_to_script, pick, reverse_endianness, roll


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
            - stack:    [{GROUP_ORDER} {Gx} {0x0220||Gx_bytes||02||02} .., {h} .., {a} .., {A}] or fail
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
        # stack out: [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02||02}, .., {h}, .., {a}, .., A, ..,
        #               0x0220||Gx_bytes||02||02 GROUP_ORDER (h + a*Gx)]
        out += (
            roll(position=-3, n_elements=1) if clean_constants else pick(position=-3, n_elements=1)
        )  # Move 0x0220||Gx_bytes||02||02 GROUP_ORDER
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
        out += Script.parse_string("OP_TUCK OP_MOD OP_OVER OP_ADD OP_OVER OP_MOD")  # Compute (h+a*Gx) % GROUP_ORDER

        # Convert (h + a*Gx) to canonical form
        # stack in:  [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02||02}, .., {h}, .., {a}, .., A, ..,
        #               0x0220||Gx_bytes||02||02 GROUP_ORDER (h + a*Gx)]
        # stack out: [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02||02}, .., {h}, .., {a}, .., A, ..,
        #               0x0220||Gx_bytes||02||02 min{(h + a*Gx), GROUP_ORDER - (h + a*Gx)}]
        out += Script.parse_string(
            "OP_DUP OP_ROT OP_TUCK OP_2 OP_DIV OP_GREATERTHAN OP_IF OP_SWAP OP_SUB OP_ELSE OP_DROP OP_ENDIF"
        )

        # Compute s part of the signature
        # stack in:  [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02||02}, .., {h}, .., {a}, .., A, ..,
        #               0x0220||Gx_bytes||02||02 min{(h + a*Gx), GROUP_ORDER - (h + a*Gx)}]
        # stack out: [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02||02}, .., {h}, .., {a}, .., A, ..,
        #               0x0220||Gx_bytes||02||02 s]
        out += Script.parse_string(
            "OP_SIZE OP_SWAP 32 OP_NUM2BIN"
        )  # Make min{(h + a*Gx), GROUP_ORDER - (h + a*Gx)} 32-bytes long
        out += reverse_endianness(32)  # Reverse the endianness
        out += Script.parse_string("0x20 OP_ROT OP_SUB OP_SPLIT OP_NIP")  # Reset s to its correct length

        # Compute the signature
        # stack in:  [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02||02}, .., {h}, .., {a}, .., A, ..,
        #               0x0220||Gx_bytes||02||02 s]
        # stack out: [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02||02}, .., {h}, .., {a}, .., A, ..,
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
            out += move(A.y.shift(1), bool_to_moving_function(is_A_rolled))  # Move A.y
            out += Script.parse_string(
                "OP_2 OP_MOD OP_IF 0x03 OP_ELSE 0x02 OP_ENDIF"
            )  # Set the first byte for compressed form
            out += move(A.x.shift(2 - 1 * is_A_rolled), bool_to_moving_function(is_A_rolled))  # Move A.x
            out += Script.parse_string("33 OP_NUM2BIN 32 OP_SPLIT OP_DROP")  # Bring A.x to 32 bytes
            out += reverse_endianness(32)
            out += Script.parse_string("OP_CAT")
        elif isinstance(A, StackBaseElement):
            out += move(A.shift(1), bool_to_moving_function(is_A_rolled))  # Move A
        else:
            msg = f"Type not supported for A: type(A): {type(A)}"
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
            - stack: {GROUP_ORDER} {Gx} {0x0220||Gx_bytes||02}, Gy, .., {h} .., {gradient} .., {a} .., {A}, ..,,
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
        # stack out: [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 {Gy}, .., h .., {gradient} .., a .., A, .., (A + G)]
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
        # stack in:  [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 {Gy}, .., h .., {gradient} .., a .., A, .., (A + G)]
        # stack out: [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 {Gy}, .., h .., {gradient} .., a .., {A}, ..,
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
        # stack in:  [GROUP_ORDER Gx 0x0220||Gx_bytes||02||02 {Gy}, .., h .., {gradient} .., a .., {A}, ..,
        #               (A + G)]
        # stack out: [{GROUP_ORDER} {Gx} {0x0220||Gx_bytes||02||02} {Gy}, .., {h} .., {gradient} .., {a} .., {A},
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
            - stack: {GROUP_ORDER} {Gx} {0x0220||Gx_bytes||02}, .., {h} .., {a} .., {A}, ..,,
            or fail
            - altstack:

        """

        check_order([h, a, A])
        _, _, is_A_rolled = bitmask_to_boolean_list(rolling_options, 3)

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
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., {A}, .., [2/3], A.x, -A]
        out += move(A, bool_to_moving_function(is_A_rolled))
        out += Script.parse_string("OP_2 OP_MOD OP_IF OP_3 OP_2 OP_ELSE OP_2 OP_3 OP_ENDIF")  # Compute A.y % 2
        out += Script.parse_string(
            "OP_ROT 33 OP_NUM2BIN 32 OP_SPLIT OP_DROP"
        )  # Move A.x on top of the stack and make it 32 bytes
        out += reverse_endianness(32)  # Reverse endianness of A.x
        out += Script.parse_string("OP_TUCK OP_CAT")  # Construct -A

        # Verify that -A = (-a + epsilon)G
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., {A}, .., [2/3], A.x, -A]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, Gy, .., h .., a, .., {A}, .., [2/3], A.x], or fail
        out += cls.verify_base_point_multiplication_up_to_epsilon(
            check_constants=False,
            clean_constants=False,
            additional_constant=0,
            h=h.shift(3 - 2 * is_A_rolled),
            a=a.shift(3 - 2 * is_A_rolled).set_negate(True),
            rolling_options=boolean_list_to_bitmask([False, False, True]),
        )

        # Verify that A = (a + epsilon)G
        # stack in:  [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02}, {Gy}, .., {h} .., {a}, .., {A}, ..,
        #               [2/3], A.x]
        # stack out: [{GROUP_ORDER}, {Gx}, {0x0220||Gx_bytes||02}, {Gy}, .., {h} .., {a}, .., {A}, ..]
        out += Script.parse_string("OP_CAT")  # Construct A
        out += cls.verify_base_point_multiplication_up_to_epsilon(
            check_constants=False,
            clean_constants=clean_constants,
            additional_constant=0,
            h=h.shift(1 - 2 * is_A_rolled),
            a=a.shift(1 - 2 * is_A_rolled),
        )

        return out

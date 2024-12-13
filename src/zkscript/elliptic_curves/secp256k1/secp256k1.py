"""secp256k1 package."""

from tx_engine import SIGHASH, Script, encode_num
from tx_engine.engine.util import GROUP_ORDER_INT, PRIME_INT, Gx, Gx_bytes, Gy

from src.zkscript.elliptic_curves.ec_operations_fq import EllipticCurveFq
from src.zkscript.elliptic_curves.secp256k1.util import (
    stack_elliptic_curve_point_to_compressed_pubkey,
    x_coordinate_to_r_component,
)
from src.zkscript.transaction_introspection.transaction_introspection import TransactionIntrospection
from src.zkscript.types.stack_elements import (
    StackBaseElement,
    StackEllipticCurvePoint,
    StackFiniteFieldElement,
    StackNumber,
)
from src.zkscript.util.utility_functions import (
    bitmask_to_boolean_list,
    boolean_list_to_bitmask,
    check_order,
)
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    bytes_to_unsigned,
    compute_mul_sub,
    enforce_mul_equal,
    int_sig_to_s_component,
    is_not_zero,
    is_not_zero_modulo,
    is_zero,
    mod,
    move,
    nums_to_script,
    pick,
    reverse_endianness_fixed_length,
    roll,
    verify_bottom_constants,
)


class Secp256k1:
    """Class containing scripts that perform scalar multiplications on secp256k1.

    Attributes:
        GROUP_ORDER (int): The order |E|, where E is secp256k1.
        Gx (int): The x coordinate of the generator of E.
        Gy (int): The y coordinate of the generator of E.
        Gx_bytes (bytes): The byte representation of Gx.
        MODULUS (int): The prime over which E is defined.
        ec_fq (EllipticCurve): The script implementation of EC arithmetic over F_MODULUS.
    """

    GROUP_ORDER: int = GROUP_ORDER_INT
    Gx: int = Gx
    Gy: int = Gy
    Gx_bytes: bytes = Gx_bytes
    MODULUS: int = PRIME_INT
    ec_fq: EllipticCurveFq = EllipticCurveFq(MODULUS, 0, 7)

    @staticmethod
    def __verify_sighash(
        clean_constants: bool,
        sig_hash_preimage: StackBaseElement,
        h: StackFiniteFieldElement,
        rolling_options: int,
        is_verify: bool,
    ) -> Script:
        """Verify that `h` is the little-endian, minimally encoded representation of `HASH256(sig_hash_preimage)`.

        Stack input:
            - stack:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h, ..]
            - altstack: []
        Stack output:
            - stack:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h, ..] or fail
            - altstack: []

        Args:
            clean_constants (bool): clean_constants (bool): If `True`, the constants GROUP_ORDER_INT, Gx, Gx_bytes are
                removed from the stack after execution. Defaults to `True`.
            sig_hash_preimage (StackBaseElement): The position in the stack of `sig_hash_preimage` of the spending
                transaction.
            h (StackFiniteFieldElement): The position in the stack of `h`.
            rolling_options (int): Bitmask detailing which of `h`, `sig_hash_preimage` should be removed from the stack
                after execution.
            is_verify (bool): If `True`, the script consumes the result of the equality check.

        Returns:
            The script that verifies that `h` is the little-endian, minimally encoded representation of
            `HASH256(sig_hash_preimage)`.
        """
        check_order([sig_hash_preimage, h])
        is_sig_hash_preimage_rolled, is_h_rolled = bitmask_to_boolean_list(rolling_options, 2)
        out = Script()

        # Compute little-endian, minimally encoded representation of HASH256(sig_hash_preimage)
        out += move(sig_hash_preimage, pick)
        out += Script.parse_string("OP_HASH256")
        out += bytes_to_unsigned(length_stack_element=32, rolling_option=True)

        # Enforce condition
        out += move(h.shift(1), bool_to_moving_function(is_h_rolled))
        out += Script.parse_string("OP_EQUALVERIFY")

        # Verify that `sig_hash_preimage` is the sig_hash_preimage of the spending transaction
        out += TransactionIntrospection.pushtx(
            sighash_value=SIGHASH.ALL_FORKID,
            sig_hash_preimage=sig_hash_preimage.shift(-is_h_rolled),
            rolling_option=is_sig_hash_preimage_rolled,
            clean_constants=clean_constants,
            verify_constants=False,
            is_checksigverify=is_verify,
            is_opcodeseparator=False,
        )

        return out

    @classmethod
    def __verify_base_point_multiplication_up_to_epsilon(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        additional_constant: int = 0,
        h: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        a: StackFiniteFieldElement = StackFiniteFieldElement(1, False, 1),  # noqa: B008
        A: StackBaseElement | StackEllipticCurvePoint = StackBaseElement(0),  # noqa: B008, N803
        rolling_options: int = (1 << 3) - 1,
    ) -> Script:
        r"""Verify that A = (± a + additional_constant + epsilon)G.

        This script verifies that A = (± a + additional_constant + epsilon)G, where:
        - A is a point on E
        - a is a scalar
        - G is the generator of secp256k1.
        - epsilon is either 0 or -2*h/Gx -2(a + additional_constant)

        Stack input:
            - stack:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h .., a .., A]
            - altstack: []
        Stack out:
            - stack:    [GROUP_ORDER Gx 0x0220||Gx_bytes||02, .., h .., a .., A] or fail
            - altstack: []

        Args:
            check_constants (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constants (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            additional_constant (int): The additional constant for which the script verifies
                A = (± a + additional_constant + epsilon)G. Defaults to `0`.
            h (StackFiniteFieldElement): The position of the sighash of the transaction in which the script is executed.
                Defaults to `StackFiniteFieldElement(2,False,1)`.
            a (StackFiniteFieldElement): The position of the constant `a` for which the script verifies
                A = (± a + additional_constant + epsilon)G. Defaults to `StackFiniteFieldElement(1, False, 1)`.
            A (StackBaseElement | StackEllipticCurvePoint): The position of the point on E for which the script
                verifies A = (± a + additional_constant + epsilon)G. Defaults to `StackBaseElement(0)`.
            rolling_options (int): Bitmask detailing which elements among `h`, `a`, and `A` should be removed from
                the stack after execution.

        Returns:
            The script that verifies A = (± a + additional_constant + epsilon)G.
        """
        check_order([h, a, A])
        is_h_rolled, is_a_rolled, is_A_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = (
            verify_bottom_constants(
                [
                    encode_num(cls.GROUP_ORDER),
                    encode_num(Gx),
                    bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"),
                ]
            )
            if check_constants
            else Script()
        )

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
    def verify_base_point_multiplication_unchecked(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        additional_constant: int = 0,
        h: StackFiniteFieldElement = StackFiniteFieldElement(3, False, 1),  # noqa: B008
        a: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        A: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = (1 << 3) - 1,
    ) -> Script:
        """Verify that A = (a+additional_constant)G.

        This script verifies that A = aG, where:
        - a is a scalar
        - G is the generator of secp256k1.

        Stack input:
            - stack: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h .., a .., A, ..]
            - altstack: []
        Stack out:
            - stack: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h .., a .., A, ..]
            or fail
            - altstack: []

        Args:
            check_constants (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constants (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            additional_constant (int): The additional constant for which the script verifies
                A = (± a + additional_constant + epsilon)G. Defaults to `0`.
            h (StackFiniteFieldElement): The position of the sighash of the transaction in which the script is executed.
                Defaults to `StackFiniteFieldElement(3, False, 1)`.
            a (StackFiniteFieldElement): The position of the constant `a` for which the script verifies
                A = aG. Defaults to `StackFiniteFieldElement(2, False, 1)`.
            A (StackEllipticCurvePoint): The position of the point on E for which the script
                verifies A = aG. Defaults to
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(1, False, 1),
                    StackFiniteFieldElement(0, False, 1),
                ),
            rolling_options (int): Bitmask detailing which elements among `h`, `a`, and `A` should be removed
                from the stack after execution.

        Returns:
            The script that verifies A = aG.

        Notes:
            This script does not verify that `A` is on secp256k1.
            This script does not verify that `h` is the sighash of the spending transaction.
        """
        check_order([h, a, A])
        is_h_rolled, is_a_rolled, is_A_rolled = bitmask_to_boolean_list(rolling_options, 3)

        out = (
            verify_bottom_constants(
                [
                    encode_num(cls.GROUP_ORDER),
                    encode_num(cls.Gx),
                    bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"),
                ]
            )
            if check_constants
            else Script()
        )

        # Enforce that a Gx != -h mod GROUP_ORDER
        # stack in:   [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h .., a, .., A, ..]
        # stack out:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h .., a, .., A, ..] or fail
        out += compute_mul_sub(
            clean_constant=False,
            is_constant_reused=False,
            a=StackFiniteFieldElement(-2, False, 1),
            b=h.set_negate(True),
            c=a,
            rolling_options=0,
            permutation=1 << 2,
        )
        out += is_not_zero()

        # Prepare A and -A
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h .., a, .., A, ..]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h .., a, .., A, ..,
        #               [2/3], A.x, -A]
        out += move(A, bool_to_moving_function(is_A_rolled))
        out += Script.parse_string("OP_2 OP_MOD OP_IF OP_3 OP_2 OP_ELSE OP_2 OP_3 OP_ENDIF")  # Compute A.y % 2
        out += Script.parse_string(
            "OP_ROT 33 OP_NUM2BIN 32 OP_SPLIT OP_DROP"
        )  # Move A.x on top of the stack and make it 32 bytes
        out += reverse_endianness_fixed_length(32)  # Reverse endianness of A.x
        out += Script.parse_string("OP_TUCK OP_CAT")  # Construct -A

        # Verify that -A = (-a - additional_constant + epsilon)G
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h .., a, .., A, ..,
        #               [2/3], A.x, -A]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h .., a, .., A, ..,
        #               [2/3], A.x], or fail
        out += cls.__verify_base_point_multiplication_up_to_epsilon(
            check_constants=False,
            clean_constants=False,
            additional_constant=-additional_constant,
            h=h.shift(3 - 2 * is_A_rolled),
            a=a.shift(3 - 2 * is_A_rolled).set_negate(True),
            rolling_options=boolean_list_to_bitmask([False, False, True]),
        )

        # Verify that A = (a + additional_constant + epsilon)G
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h .., a, .., A, ..,
        #               [2/3], A.x]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., sig_hash_preimage, .., h .., a, .., A, ..]
        out += Script.parse_string("OP_CAT")  # Construct A
        out += cls.__verify_base_point_multiplication_up_to_epsilon(
            check_constants=False,
            clean_constants=clean_constants,
            additional_constant=additional_constant,
            h=h.shift(1 - 2 * is_A_rolled),
            a=a.shift(1 - 2 * is_A_rolled),
            rolling_options=boolean_list_to_bitmask([is_h_rolled, is_a_rolled, True]),
        )

        return out

    @classmethod
    def verify_base_point_multiplication(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        additional_constant: int = 0,
        sig_hash_preimage: StackBaseElement = StackBaseElement(4),  # noqa: B008
        h: StackFiniteFieldElement = StackFiniteFieldElement(3, False, 1),  # noqa: B008
        a: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        A: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = (1 << 4) - 1,
    ) -> Script:
        """Verify that A = (a+additional_constant)G.

        This script verifies that A = aG, where:
        - A is a point on E.
        - a is a scalar
        - G is the generator of secp256k1.

        Stack input:
            - stack: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, MODULUS, .., h .., a .., A, ..]
            - altstack: []
        Stack out:
            - stack: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, MODULUS, .., h .., a .., A, ..]
            or fail
            - altstack: []

        Args:
            check_constants (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constants (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            additional_constant (int): The additional constant for which the script verifies
                A = (± a + additional_constant + epsilon)G. Defaults to `0`.
            sig_hash_preimage (StackBaseElement): The position in the stack of `sig_hash_preimage` of the spending
                transaction. Defaults to `StackBaseElement(4)`
            h (StackFiniteFieldElement): The position of the sighash of the transaction in which the script is executed.
                Defaults to `StackFiniteFieldElement(3, False, 1)`.
            a (StackFiniteFieldElement): The position of the constant `a` for which the script verifies
                A = aG. Defaults to `StackFiniteFieldElement(2, False, 1)`.
            A (StackEllipticCurvePoint): The position of the point on E for which the script
                verifies A = aG. Defaults to
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(1, False, 1),
                    StackFiniteFieldElement(0, False, 1),
                ),
            rolling_options (int): Bitmask detailing which elements among `sig_hash_preimage`, `h`, `a`, and `A`
                should be removed from the stack after execution.

        Returns:
            The script that verifies A = aG.
        """
        check_order([sig_hash_preimage, h, a, A])
        is_sig_hash_preimage_rolled, is_h_rolled, is_a_rolled, is_A_rolled = bitmask_to_boolean_list(rolling_options, 4)

        out = (
            verify_bottom_constants(
                [
                    encode_num(cls.GROUP_ORDER),
                    encode_num(cls.Gx),
                    bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"),
                    encode_num(cls.MODULUS),
                ]
            )
            if check_constants
            else Script()
        )

        out += cls.ec_fq.is_on_curve(
            check_constant=False,
            clean_constant=clean_constants,
            modulus=StackNumber(-4, False),
            P=A,
            rolling_option=False,
        )

        out += cls.verify_base_point_multiplication_unchecked(
            check_constants=False,
            clean_constants=False,
            additional_constant=additional_constant,
            h=h,
            a=a,
            A=A,
            rolling_options=boolean_list_to_bitmask([False, is_a_rolled, is_A_rolled]),
        )

        # Verify that h is the sighash and leave result on the stack
        out += cls.__verify_sighash(
            clean_constants=clean_constants,
            sig_hash_preimage=sig_hash_preimage.shift(-is_a_rolled - 2 * is_A_rolled),
            h=h.shift(-is_a_rolled - 2 * is_A_rolled),
            rolling_options=boolean_list_to_bitmask([is_sig_hash_preimage_rolled, is_h_rolled]),
            is_verify=False,
        )

        return out

    @classmethod
    def verify_point_multiplication_up_to_sign(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        sig_hash_preimage: StackBaseElement = StackBaseElement(11),  # noqa: B008
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
        rolling_options: int = (1 << 9) - 1,
    ) -> Script:
        """Verify Q = ± b * P.

        Stack input:
            - stack: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, MODULUS, .., h, .., b,
                        x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient, ..,
                            Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..]
            - altstack: []
        Stack output:
            - stack: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, MODULUS, .., h, .., b,
                        x_coordinate_target_times_b_inverse, .., h_times_x_coordinate_target_inverse, .., gradient, ..,
                            Q, .. P, .., h_times_x_coordinate_target_inverse_times_G, ..] or fail
            - altstack: []

        Args:
            check_constants (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constants (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            sig_hash_preimage (StackBaseElement): The position in the stack of `sig_hash_preimage` of the spending
                transaction. Defaults to `StackBaseElement(11)`
            h (StackFiniteFieldElement): The position of the sighash of the transaction in which the script is executed.
                Defaults to `StackFiniteFieldElement(10, False, 1)`.
            b (StackFiniteFieldElement): The position of the constant `b` for which the script verifies
                Q = ± b * P. Defaults to `StackFiniteFieldElement(9, False, 1)`.
            x_coordinate_target_times_b_inverse (StackFiniteFieldElement): The position in the stack of the x coordinate
                of `Q` times the inverse of `b` modulo `GROUP_ORDER`. Defaults to
                    `StackFiniteFieldElement(8, False, 1)`.
            h_times_x_coordinate_target_inverse (StackFiniteFieldElement): The position in the stack of `h` times the
                inverse of the x coordinate of `Q` modulo `GROUP_ORDER`. Defaults to
                    `StackFiniteFieldElement(7, False, 1)`.
            gradient (StackFiniteFieldElement): The position in the stack of the gradient through `P` and
                `x_coordinate_target_times_b_inverse` * `G`. Defaults to
                    `StackFiniteFieldElement(6, False, 1)`.
            Q (StackEllipticCurvePoint): The position in the stack of the point `Q` for which the script verifies
                Q = ± b * P. Defaults to:
                    `StackEllipticCurvePoint(
                        StackFiniteFieldElement(5, False, 1),
                        StackFiniteFieldElement(4, False, 1),
                    )`
            P (StackEllipticCurvePoint): The position in the stack of the point `P` for which the script verifies
                Q = ± b * P. Defaults to:
                    `StackEllipticCurvePoint(
                        StackFiniteFieldElement(3, False, 1),
                        StackFiniteFieldElement(2, False, 1),
                    )`
            h_times_x_coordinate_target_inverse_times_G (StackEllipticCurvePoint): The position in the stack of the
                point `h_times_x_coordinate_target_inverse` * `G`. Defaults to:
                    `StackEllipticCurvePoint(
                        StackFiniteFieldElement(1, False, 1),
                        StackFiniteFieldElement(0, False, 1),
                    )`
            rolling_options (int): Bitmask detailing which of the elements used by the script should be removed
                from the stack after execution.

        Returns:
            The script that verifies Q = ± b * P.

        Note:
            This function does not handle the case in which b = 0 mod n.
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
        list_rolling_options = bitmask_to_boolean_list(rolling_options, 9)

        out = (
            verify_bottom_constants(
                [
                    encode_num(cls.GROUP_ORDER),
                    encode_num(cls.Gx),
                    bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"),
                    encode_num(cls.MODULUS),
                ]
            )
            if check_constants
            else Script()
        )

        # Verify that Q, P, h_times_x_coordinate_target_inverse_times_G are on the curve
        for i, point in enumerate([Q, P, h_times_x_coordinate_target_inverse_times_G]):
            out += cls.ec_fq.evaluate_curve_equation(
                check_constant=False,
                clean_constant=False,
                modulus=StackNumber(-4, False),
                P=point.shift(i),
                rolling_option=False,
            )
        out += Script.parse_string(" ".join(["OP_CAT"] * i))
        out += is_zero()

        # Verify that MODULUS - GROUP_ORDER < Q_x < GROUP_ORDER
        out += move(Q.x, pick)  # Pick Q_x
        out += pick(position=-4, n_elements=1)  # Move MODULUS
        out += pick(position=-1, n_elements=1)  # Move GROUP_ORDER
        out += Script.parse_string("OP_TUCK OP_SUB OP_SWAP")  # Duplicate GROUP_ORDER, compute MODULUS - GROUP_ORDER
        out += Script.parse_string("OP_WITHIN OP_VERIFY")

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
            modulus=StackNumber(-4, False),
            gradient=gradient,
            P=P,
            Q=h_times_x_coordinate_target_inverse_times_G.set_negate(True),
            rolling_options=boolean_list_to_bitmask([list_rolling_options[5], list_rolling_options[7], False]),
        )
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # Verify that b != 0 mod n
        out += is_not_zero_modulo(clean_constant=False, stack_element=b, rolling_option=False)

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
            x_coordinate_target_times_b_inverse.shift(-list_rolling_options[5] - 2 * list_rolling_options[7]),
            bool_to_moving_function(list_rolling_options[3]),
        )  # Move x_coordinate_target_times_b_inverse
        out += Script.parse_string("OP_DUP OP_TOALTSTACK")
        out += move(
            b.shift(-list_rolling_options[3] - list_rolling_options[5] - 2 * list_rolling_options[7] + 1),
            bool_to_moving_function(list_rolling_options[2]),
        )  # Move b
        out += Script.parse_string("OP_MUL")  # Compute x_coordinate_target_times_b_inverse * b
        out += move(
            Q.x.shift(-2 * list_rolling_options[7] + 1), bool_to_moving_function(list_rolling_options[6])
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
                -list_rolling_options[2]
                - list_rolling_options[3]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - 2 * list_rolling_options[7]
                + 2
            ),
            pick,
        )  # Pick h
        out += move(
            h_times_x_coordinate_target_inverse.shift(
                -list_rolling_options[5] - list_rolling_options[6] - 2 * list_rolling_options[7] + 3
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
        out += cls.verify_base_point_multiplication_unchecked(
            check_constants=False,
            clean_constants=False,
            h=h.shift(
                -list_rolling_options[2]
                - list_rolling_options[3]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - 2 * list_rolling_options[7]
            ),
            a=h_times_x_coordinate_target_inverse.shift(
                -list_rolling_options[5] - list_rolling_options[6] - 2 * list_rolling_options[7]
            ),
            A=h_times_x_coordinate_target_inverse_times_G,
            rolling_options=boolean_list_to_bitmask([False, list_rolling_options[4], list_rolling_options[8]]),
        )

        if list_rolling_options[6]:
            out += move(Q.y.shift(-2 * list_rolling_options[7] - 2 * list_rolling_options[8]), roll)
            out += Script.parse_string("OP_DROP")

        # Verify that h is the sighash and leave result on the stack
        out += cls.__verify_sighash(
            clean_constants=clean_constants,
            sig_hash_preimage=sig_hash_preimage.shift(
                -list_rolling_options[2]
                - list_rolling_options[3]
                - list_rolling_options[4]
                - list_rolling_options[5]
                - 2 * list_rolling_options[6]
                - 2 * list_rolling_options[7]
                - 2 * list_rolling_options[8]
            ),
            h=h.shift(
                -list_rolling_options[2]
                - list_rolling_options[3]
                - list_rolling_options[4]
                - list_rolling_options[5]
                - 2 * list_rolling_options[6]
                - 2 * list_rolling_options[7]
                - 2 * list_rolling_options[8]
            ),
            rolling_options=boolean_list_to_bitmask([list_rolling_options[0], list_rolling_options[1]]),
            is_verify=False,
        )

        return out

    @classmethod
    def verify_point_multiplication(
        cls,
        check_constants: bool = False,
        clean_constants: bool = False,
        sig_hash_preimage: StackBaseElement = StackBaseElement(19),  # noqa: B008
        h: StackFiniteFieldElement = StackFiniteFieldElement(18, False, 1),  # noqa: B008
        s: tuple[StackFiniteFieldElement] = (
            StackFiniteFieldElement(17, False, 1),
            StackFiniteFieldElement(16, False, 1),
        ),
        gradients: tuple[StackFiniteFieldElement] = (
            StackFiniteFieldElement(15, False, 1),
            StackFiniteFieldElement(14, False, 1),
            StackFiniteFieldElement(13, False, 1),
        ),
        d: tuple[StackFiniteFieldElement] = (
            StackFiniteFieldElement(12, False, 1),
            StackFiniteFieldElement(11, False, 1),
        ),
        D: tuple[StackEllipticCurvePoint] = (  # noqa: N803
            StackEllipticCurvePoint(
                StackFiniteFieldElement(10, False, 1),
                StackFiniteFieldElement(9, False, 1),
            ),
            StackEllipticCurvePoint(
                StackFiniteFieldElement(8, False, 1),
                StackFiniteFieldElement(7, False, 1),
            ),
            StackEllipticCurvePoint(
                StackFiniteFieldElement(6, False, 1),
                StackFiniteFieldElement(5, False, 1),
            ),
        ),
        Q: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(4, False, 1),  # noqa: B008
            StackFiniteFieldElement(3, False, 1),  # noqa: B008
        ),
        b: StackFiniteFieldElement = StackFiniteFieldElement(2, False, 1),  # noqa: B008
        P: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
            StackFiniteFieldElement(1, False, 1),  # noqa: B008
            StackFiniteFieldElement(0, False, 1),  # noqa: B008
        ),
        rolling_options: int = (1 << 15) - 1,
    ) -> Script:
        """Verify Q = bP.

        Stack input:
            - stack: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, MODULUS, .. h, .., s, .., gradients,
                        .., d, .., D, .., Q, .., b, .., P, ..]
            - altstack: []
        Stack output:
            - stack: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, MODULUS, .. h, .., s, .., gradients,
                        .., d, .., D, .., Q, .., b, .., P, ..] or fail
            - altstack: []

        Args:
            check_constants (bool | None): If `True`, check if `q` is valid before proceeding. Defaults to `None`.
            clean_constants (bool | None): If `True`, remove `q` from the bottom of the stack. Defaults to `None`.
            sig_hash_preimage (StackBaseElement): The position in the stack of `sig_hash_preimage` of the spending
                transaction. Defaults to `StackBaseElement(19)`
            h (StackFiniteFieldElement): The position of the sighash of the transaction in which the script is executed.
                Defaults to `StackFiniteFieldElement(18, False, 1)`.
            s (tuple[StackFiniteFieldElement]): The position in the stack of:
                    s[0] = Q_x / b mod GROUP_ORDER, s[1] = (Q + bG)_x / b mod GROUP_ORDER
                in the stack. Defaults to:
                `(
                    StackFiniteFieldElement(17, False, 1),
                    StackFiniteFieldElement(16, False, 1),
                `),
            gradients (tuple[StackFiniteFieldElement]): The position in the stack of:
                    gradients[0] = The gradient through `P` and `D[0]`
                    gradients[1] = The gradient through `P` and `D[1]`
                    gradients[2] = The gradient through `P` and `D[2]`
                Defaults to:
                `(
                    StackFiniteFieldElement(15, False, 1),
                    StackFiniteFieldElement(14, False, 1),
                    StackFiniteFieldElement(13, False, 1),
                `)
            d (list[StackFiniteFieldElement]): The position in the stack of:
                    d[0] = h / Q_x mod GROUP_ORDER, d[1] = h / (Q + bG)_x mod GROUP_ORDER
                Defaults to:
                `(
                    StackFiniteFieldElement(12, False, 1),
                    StackFiniteFieldElement(11, False, 1),
                `)
            D (tuple[StackEllipticCurvePoint]): The position in the stack of:
                    D[0] = (h / Q_x)*G, D[1] = (h / (Q + bG)_x) * G, D[2] = b * G
                Defaults to:
                `(
                    StackEllipticCurvePoint(
                        StackFiniteFieldElement(10, False, 1),
                        StackFiniteFieldElement(9, False, 1),
                    ),
                    StackEllipticCurvePoint(
                        StackFiniteFieldElement(8, False, 1),
                        StackFiniteFieldElement(7, False, 1),
                    ),
                    StackEllipticCurvePoint(
                        StackFiniteFieldElement(6, False, 1),
                        StackFiniteFieldElement(5, False, 1),
                    ),
                )`
            Q (StackEllipticCurvePoint): The position in the stack of the point `Q` for which the script verifies
                Q = b * P. Defaults to:
                `StackEllipticCurvePoint(
                    StackFiniteFieldElement(4, False, 1),
                    StackFiniteFieldElement(3, False, 1),
                )`
            b (StackFiniteFieldElement): The position in the stack of the element `b` for which the script verifies
                Q = b * P. Defaults to: `StackFiniteFieldElement(2, False, 1)`.
            P (StackEllipticCurvePoint): The position in the stack of the point `P` for which the script verifies
                Q = ± b * P. Defaults to:
                    `StackEllipticCurvePoint(
                        StackFiniteFieldElement(1, False, 1),
                        StackFiniteFieldElement(0, False, 1),
                    )`
            rolling_options (int): Bitmask detailing which of the elements used by the script should be removed
                from the stack after execution.

        Returns:
            The script that verifies Q = b * P.

        Notes:
            This script removes MODULUS from the bottom of the stack after execution.
            This script does not handle the case b = 0 mod GROUP_ORDER.
            This script only handles the case MODULUS - GROUP_ORDER < Q_x, (Q + bG)_x < GROUP_ORDER.
        """
        check_order([h, *s, *gradients, *d, *D, Q, b, P])
        list_rolling_options = bitmask_to_boolean_list(rolling_options, 15)

        out = (
            verify_bottom_constants(
                [
                    encode_num(cls.GROUP_ORDER),
                    encode_num(cls.Gx),
                    bytes.fromhex("0220") + cls.Gx_bytes + bytes.fromhex("02"),
                    encode_num(cls.MODULUS),
                ]
            )
            if check_constants
            else Script()
        )

        # Verify that D[0], D[1], D[2], Q, P are on the curve
        for i, point in enumerate([*D, Q, P]):
            out += cls.ec_fq.evaluate_curve_equation(
                check_constant=False,
                clean_constant=False,
                modulus=StackNumber(-4, False),
                P=point.shift(i),
                rolling_option=False,
            )
        out += Script.parse_string(" ".join(["OP_CAT"] * i))
        out += is_zero()

        # Verify that b != 0 mod n
        out += is_not_zero_modulo(
            clean_constant=False, modulus=StackNumber(-2, False), stack_element=b, rolling_option=False
        )

        # Verify that MODULUS - GROUP_ORDER < Q_x < GROUP_ORDER
        out += move(Q.x, pick)  # Pick Q_x
        out += pick(position=-4, n_elements=1)  # Move MODULUS
        out += pick(position=-1, n_elements=1)  # MoveGROUP_ORDER
        out += Script.parse_string(
            "OP_TUCK OP_SUB OP_SWAP OP_WITHIN OP_VERIFY"
        )  # Verify MODULUS - GROUP_ORDER < Q_x < GROUP_ORDER

        # compute P - D[0]
        # stack in:  [MODULUS, GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P]
        # stack out: [MODULUS, GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P]
        # altstack out: [P - D[0]]
        out += cls.ec_fq.point_algebraic_addition(
            take_modulo=True,
            check_constant=False,
            clean_constant=False,
            verify_gradient=True,
            modulus=StackNumber(-4, False),
            gradient=gradients[0],
            P=D[0].set_negate(True),
            Q=P,
            rolling_options=boolean_list_to_bitmask([list_rolling_options[4], False, False]),
        )
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # compute P - D[1]
        # stack in:  [MODULUS, GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P] or fail
        # altstack out: [P - D[0], P - D[1]]
        out += cls.ec_fq.point_algebraic_addition(
            take_modulo=True,
            check_constant=False,
            clean_constant=False,
            verify_gradient=True,
            modulus=StackNumber(-4, False),
            gradient=gradients[1],
            P=D[1].set_negate(True),
            Q=P,
            rolling_options=boolean_list_to_bitmask([list_rolling_options[5], False, list_rolling_options[14]]),
        )
        out += Script.parse_string("OP_TOALTSTACK OP_TOALTSTACK")

        # compute Q + D[2]
        # stack in:  [MODULUS, GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, (Q + D[2])_x] or fail
        # altstack out: [P - D[0], P - D[1]]
        out += cls.ec_fq.point_algebraic_addition(
            take_modulo=True,
            check_constant=False,
            clean_constant=False,
            verify_gradient=True,
            modulus=StackNumber(-4, False),
            gradient=gradients[2].shift(-2 * list_rolling_options[14]),
            P=D[2].shift(-2 * list_rolling_options[14]),
            Q=Q.shift(-2 * list_rolling_options[14]),
            rolling_options=boolean_list_to_bitmask([list_rolling_options[6], False, False]),
        )
        out += Script.parse_string("OP_DROP")

        # Verify MODULUS - GROUP_ORDER < (Q + D[2])_x < GROUP_ORDER
        # stack in:     [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, (Q + D[2])_x]
        # altstack in:  [P - D[0], P - D[1]]
        # stack out:    [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P] or fail
        # altstack out: [P - D[0], P - D[1], (Q + D[2])_x]
        out += pick(position=0, n_elements=1)  # Duplicate (Q + D[2])_x
        out += move(StackNumber(-4, False), bool_to_moving_function(clean_constants))  # Move MODULUS
        out += pick(position=-1, n_elements=1)  # Pick GROUP_ORDER
        out += Script.parse_string(
            "OP_TUCK OP_SUB OP_SWAP OP_WITHIN OP_VERIFY OP_TOALTSTACK"
        )  # Verify MODULUS - GROUP_ORDER < (Q + D[2])_x < GROUP_ORDER and place (Q + D[2])_x on the altstack

        # verify D[0] = d[0] * G
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P] or fail
        # altstack out: [P - D[0], P - D[1], (Q + D[2])_x]
        out += cls.verify_base_point_multiplication_unchecked(
            check_constants=False,
            clean_constants=False,
            h=h.shift(
                -list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - 2 * list_rolling_options[14]
            ),
            a=d[0].shift(-2 * list_rolling_options[14]),
            A=D[0].shift(-2 * list_rolling_options[14]),
            rolling_options=boolean_list_to_bitmask([False, False, list_rolling_options[9]]),
        )

        # verify D[1] = (d[1]-1)* G
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P] or fail
        # altstack out: [P - D[0], P - D[1], (Q + D[2])_x]
        out += cls.verify_base_point_multiplication_unchecked(
            check_constants=False,
            clean_constants=False,
            additional_constant=-1,
            h=h.shift(
                -list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[14]
            ),
            a=d[1].shift(-2 * list_rolling_options[9] - 2 * list_rolling_options[14]),
            A=D[1].shift(-2 * list_rolling_options[14]),
            rolling_options=boolean_list_to_bitmask([False, False, list_rolling_options[10]]),
        )

        # verify D[2] = b * G
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P] or fail
        # altstack out: [P - D[0], P - D[1], (Q + D[2])_x]
        out += move(
            D[2].shift(-2 * list_rolling_options[14]), bool_to_moving_function(list_rolling_options[11])
        )  # Move D[2]
        out += cls.verify_base_point_multiplication_unchecked(
            check_constants=False,
            clean_constants=False,
            additional_constant=0,
            h=h.shift(
                -list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - 2 * list_rolling_options[14]
                + 2
            ),
            a=b.shift(-2 * list_rolling_options[14] + 2),
            rolling_options=boolean_list_to_bitmask([False, False, True]),
        )

        # verify d[1] * (Q + bG)_x = h mod GROUP_ORDER
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, (Q + D[2])_x] or fail
        # altstack out: [P - D[0], P - D[1]]
        out += Script.parse_string("OP_FROMALTSTACK")
        out += enforce_mul_equal(
            clean_constant=False,
            is_constant_reused=False,
            a=h.shift(
                -list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - 2 * list_rolling_options[14]
                + 1
            ),
            b=d[1].shift(
                -2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - 2 * list_rolling_options[14]
                + 1
            ),
            rolling_options=boolean_list_to_bitmask([False, list_rolling_options[8], False]),
            leave_on_top_of_stack=0,
            equation_to_check=(1 << 0),
        )

        # verify s[1] * b = (Q + bG)_x mod GROUP_ORDER
        # stack in:  [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, (Q + D[2])_x]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, (Q + D[2])_x, s[0]] or fail
        # altstack out: [P - D[0], P - D[1]]
        out += enforce_mul_equal(
            clean_constant=False,
            is_constant_reused=False,
            a=s[1].shift(
                -list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - list_rolling_options[8]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - 2 * list_rolling_options[14]
                + 1
            ),
            b=b.shift(-2 * list_rolling_options[14] + 1),
            rolling_options=boolean_list_to_bitmask([list_rolling_options[3], False, False]),
            leave_on_top_of_stack=1,
            equation_to_check=(1 << 1),
        )

        # verify that Der((Q + bG)_x,s[1]) is valid for compressed(P - D[1])
        # stack in: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, (Q + D[2])_x, s[0]]
        # altstack in: [P - D[0], P - D[1]]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P] or fail
        # altstack out: [P - D[0]]
        out += int_sig_to_s_component(group_order=StackNumber(-1, False), rolling_options=2, add_prefix=True)
        out += Script.parse_string("OP_TOALTSTACK")
        out += x_coordinate_to_r_component()
        out += Script.parse_string("OP_FROMALTSTACK")
        out += Script.parse_string("OP_CAT OP_SIZE OP_SWAP OP_CAT 0x30 OP_SWAP OP_CAT 0x41 OP_CAT")
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")
        out += stack_elliptic_curve_point_to_compressed_pubkey()
        out += Script.parse_string("OP_CHECKSIGVERIFY")

        # verify d[0] * x_Q = h mod GROUP_ORDER
        # stack in: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P] or fail
        # altstack in: [P - D[0]]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, x_Q] or fail
        # altstack out: [P - D[0]]
        out += enforce_mul_equal(
            clean_constant=False,
            is_constant_reused=False,
            a=h.shift(
                -list_rolling_options[3]
                - list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - list_rolling_options[8]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - 2 * list_rolling_options[14]
            ),
            b=d[0].shift(
                -list_rolling_options[8]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - 2 * list_rolling_options[14]
            ),
            c=Q.x.shift(-2 * list_rolling_options[14]),
            rolling_options=boolean_list_to_bitmask([False, list_rolling_options[7], list_rolling_options[12]]),
            leave_on_top_of_stack=4,
            equation_to_check=(1 << 0),
        )

        # verify s[0] * b = x_Q mod GROUP_ORDER
        # stack in: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, x_Q]
        # altstack in: [P - D[0]]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, x_Q, s[0]] or fail
        # altstack out: [P - D[0]]
        out += enforce_mul_equal(
            clean_constant=False,
            is_constant_reused=False,
            a=s[0].shift(
                -list_rolling_options[3]
                - list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - list_rolling_options[7]
                - list_rolling_options[8]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - list_rolling_options[12]
                - 2 * list_rolling_options[14]
                + 1
            ),
            b=b.shift(-2 * list_rolling_options[14] + 1),
            rolling_options=boolean_list_to_bitmask([list_rolling_options[2], list_rolling_options[13], False]),
            leave_on_top_of_stack=1,
            equation_to_check=(1 << 1),
        )

        # verify that Der(x_Q,s[0]) is valid for compressed(P - D[0])
        # stack in: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P, x_Q, s[0]]
        # altstack in: [P - D[0]]
        # stack out: [GROUP_ORDER, Gx, 0x0220||Gx_bytes||02, .., h, s[:],
        #               gradients[:], d[:], D[:], Q, b, P] or fail
        # altstack out: []
        out += int_sig_to_s_component(group_order=StackNumber(-1, False), rolling_options=2, add_prefix=True)
        out += Script.parse_string("OP_TOALTSTACK")
        out += x_coordinate_to_r_component()
        out += Script.parse_string("OP_FROMALTSTACK")
        out += Script.parse_string("OP_CAT OP_SIZE OP_SWAP OP_CAT 0x30 OP_SWAP OP_CAT 0x41 OP_CAT")
        out += Script.parse_string("OP_FROMALTSTACK OP_FROMALTSTACK")
        out += stack_elliptic_curve_point_to_compressed_pubkey()
        out += Script.parse_string("OP_CHECKSIGVERIFY")

        if list_rolling_options[12]:
            out += move(
                Q.y.shift(-list_rolling_options[13] - 2 * list_rolling_options[14]),
                bool_to_moving_function(list_rolling_options[12]),
            )  # Move Q.y
            out += Script.parse_string("OP_DROP")

        # Verify that h is the sighash and leave result on the stack
        out += cls.__verify_sighash(
            clean_constants=clean_constants,
            sig_hash_preimage=sig_hash_preimage.shift(
                -list_rolling_options[2]
                - list_rolling_options[3]
                - list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - list_rolling_options[7]
                - list_rolling_options[8]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - 2 * list_rolling_options[12]
                - list_rolling_options[13]
                - 2 * list_rolling_options[14]
            ),
            h=h.shift(
                -list_rolling_options[2]
                - list_rolling_options[3]
                - list_rolling_options[4]
                - list_rolling_options[5]
                - list_rolling_options[6]
                - list_rolling_options[7]
                - list_rolling_options[8]
                - 2 * list_rolling_options[9]
                - 2 * list_rolling_options[10]
                - 2 * list_rolling_options[11]
                - 2 * list_rolling_options[12]
                - list_rolling_options[13]
                - 2 * list_rolling_options[14]
            ),
            rolling_options=boolean_list_to_bitmask([list_rolling_options[0], list_rolling_options[1]]),
            is_verify=False,
        )

        return out

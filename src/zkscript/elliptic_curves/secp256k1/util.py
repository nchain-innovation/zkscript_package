from tx_engine import Script

from src.zkscript.types.stack_elements import (
    StackEllipticCurvePoint,
    StackFiniteFieldElement,
    StackNumber,
)
from src.zkscript.util.utility_functions import (
    bitmask_to_boolean_list,
)
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    move,
    pick,
    reverse_endianness,
    reverse_endianness_unknown_length,
    roll,
)


def stack_elliptic_curve_point_to_compressed_pubkey(
    A: StackEllipticCurvePoint = StackEllipticCurvePoint(  # noqa: B008, N803
        StackFiniteFieldElement(1, False, 1),  # noqa: B008
        StackFiniteFieldElement(0, False, 1),  # noqa: B008
    ),
    rolling_option: bool = True,
) -> Script:
    """Return the script that transforms A = (x,y) into a compressed public key.

    Stack input:
        - stack:    [.., A, ..]
        - altstack: []
    Stack output:
        - stack:    [.., {A}, .., compressed(A)]
        - altstack: []

    Args:
        A (StackEllipticCurvePoint): The elliptic curve point that will be turned into a compressed
            public key. Defaults to:
                StackEllipticCurvePoint(
                    StackFiniteFieldElement(1,False,1),
                    StackFiniteFieldElement(0,False,1),
                ),
        rolling_option (bool): Whether to roll A or not. Defaults to `True`.

    """
    out = move(A.y, bool_to_moving_function(rolling_option))  # Move A.y
    out += Script.parse_string("OP_2 OP_MOD OP_IF 0x03 OP_ELSE 0x02 OP_ENDIF")  # Set the first byte for compressed form
    out += move(A.x.shift(1 - 1 * rolling_option), bool_to_moving_function(rolling_option))  # Move A.x
    out += Script.parse_string(
        "33 OP_NUM2BIN 32 OP_SPLIT OP_DROP"
    )  # Bring A.x to 32 bytes - need 33 OP_NUM2BIN because A.x might not fit in 32 bytes as a
    # minimally encoded number
    out += reverse_endianness(32)
    out += Script.parse_string("OP_CAT")

    return out


def int_sig_to_s_component(
    group_order: StackNumber = StackNumber(1, False),  # noqa: B008
    int_sig: StackNumber = StackNumber(0, False),  # noqa: B008
    rolling_options: int = 3,
    add_prefix: bool = True,
) -> Script:
    """Return the script that transforms int_sig to the s-component of a secp256k1 ECDSA signature.

    Args:
        group_order (StackNumber): The position in the stack of the group order of secp256k1. Defaults
            to `StackNumber(1,False)`.
        int_sig (StackNumber): The position in the stack of int_sig. Defaults to `StackNumber(0,False)`.
        rolling_options (int): Whether or not to roll group_order and int_sig, defaults to 3 (roll everything).
        add_prefix (bool): Whether or not to prepend s with 0x02||len(s). Defaults to `True`.

    """

    is_group_order_rolled, is_int_sig_rolled = bitmask_to_boolean_list(rolling_options, 2)

    if [int_sig.position, group_order.position] == [1, 0]:
        # stack in:  [.., int_sig, group_order]
        # stack in:  [.., int_sig, group_order, int_sig, group_order]
        out = Script.parse_string("OP_2DUP")
    elif [int_sig.position, group_order.position] == [0, 1] and all([is_group_order_rolled, is_int_sig_rolled]):
        # stack in:  [.., group_order, int_sig]
        # stack in:  [.., int_sig, group_order, int_sig, group_order]
        out = Script.parse_string("OP_SWAP OP_2DUP")
    else:
        # stack in:  [.., group_order, .., int_sig, ..]
        # stack out: [.., group_order, .., int_sig, .., int_sig, group_order, int_sig, group_order]
        out = move(int_sig, bool_to_moving_function(is_int_sig_rolled))  # Move int_sig
        out = Script.parse_string("OP_DUP")  # Duplicate int_sig
        out += move(
            group_order.shift(2 - is_int_sig_rolled if group_order.position >= 0 else 0),
            bool_to_moving_function(is_group_order_rolled),
        )  # Move group_order
        out += Script.parse_string("OP_TUCK")

    # Put int_sig in canonical form
    # stack in:  [.., group_order, .., int_sig, ..]
    # stack out: [.., {group_order}, .., {int_sig}, .., min{int_sig, group_order - int_sig}]
    out += Script.parse_string("OP_2 OP_DIV OP_GREATERTHAN OP_IF OP_SWAP OP_SUB OP_ELSE OP_DROP OP_ENDIF")

    # Reverse endianness of min{int_sig, group_order - int_sig}
    # stack in:  [.., {group_order}, .., {int_sig}, .., min{int_sig, group_order - int_sig}]
    # stack out: [.., {group_order}, .., {int_sig}, .., s]
    out += reverse_endianness_unknown_length(max_length=32)

    if add_prefix:
        out += Script.parse_string("OP_SIZE OP_SWAP OP_CAT")  # Compute len(s)||s
        out.append_pushdata(bytes.fromhex("02"))
        out += Script.parse_string("OP_SWAP OP_CAT")  # Compute 02||len(s)||s

    return out


def x_coordinate_to_r_component(
    x_coordinate: StackNumber = StackNumber(0, False),  # noqa: B008
    rolling_option: bool = True,
    add_prefix: bool = True,
) -> Script:
    """Return the script that turns the x_coordinate a EC point to the r-component of a secp256k1 ECDSA signature.

    Args:
        x_coordinate (StackNumber): The position in the stack of the x_coordinate. Defaults
            to `StackNumber(0,False)`.
        rolling_option (int): Whether or not to roll x_coordinate, defaults to `True`.
        add_prefix (bool): Whether or not to prepend r with 0x02||len(r). Defaults to `True`.

    """

    out = move(x_coordinate, roll if rolling_option else pick)  # Move x_coordinate
    if add_prefix:
        out += Script.parse_string("OP_SIZE OP_SWAP")
    out += reverse_endianness_unknown_length(max_length=33)
    if add_prefix:
        out += Script.parse_string("OP_CAT")  # Compute len(r)||r
        out += Script.parse_string("0x02 OP_SWAP OP_CAT")  # Compute 02||len(s)||s

    return out

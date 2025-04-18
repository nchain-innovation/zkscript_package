"""Utility scritps for secp256k1 package."""

from tx_engine import Script

from src.zkscript.script_types.stack_elements import (
    StackEllipticCurvePoint,
    StackFiniteFieldElement,
    StackNumber,
)
from src.zkscript.util.utility_scripts import (
    bool_to_moving_function,
    move,
    pick,
    reverse_endianness_bounded_length,
    reverse_endianness_fixed_length,
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

    If A = (x,y), its compressed form is: 02||x if y is even, else 03||x, where || denotes string
    concatenation.

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
        rolling_option (bool): If `True`, A is removed from the stack after execution. Defaults to `True`.

    """
    out = move(A.y, bool_to_moving_function(rolling_option))  # Move A.y
    out += Script.parse_string("OP_2 OP_MOD OP_IF OP_3 OP_ELSE OP_2 OP_ENDIF")  # Set the first byte for compressed form
    out += move(A.x.shift(1 - 1 * rolling_option), bool_to_moving_function(rolling_option))  # Move A.x
    out += Script.parse_string(
        "0x21 OP_NUM2BIN 0x20 OP_SPLIT OP_DROP"
    )  # Bring A.x to 32 bytes - need 33 OP_NUM2BIN because A.x might not fit in 32 bytes as a
    # minimally encoded number
    out += reverse_endianness_fixed_length(32)
    out += Script.parse_string("OP_CAT")

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
        rolling_option (int): If `True`, the x_coordinate is removed from the stack after execution.
            Defaults to `True`.
        add_prefix (bool): Whether or not to prepend r with 0x02||len(r). Defaults to `True`.

    """
    out = move(x_coordinate, roll if rolling_option else pick)  # Move x_coordinate
    if add_prefix:
        out += Script.parse_string("OP_SIZE OP_SWAP")
    out += reverse_endianness_bounded_length(max_length=33)
    if add_prefix:
        out += Script.parse_string("OP_CAT")  # Compute len(r)||r
        out += Script.parse_string("OP_2 OP_SWAP OP_CAT")  # Compute 02||len(s)||s

    return out

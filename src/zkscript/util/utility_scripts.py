"""Utility functions to construct script."""

from typing import Union

from tx_engine import Script, encode_num
from tx_engine.engine.op_codes import (
    OP_0,
    OP_1,
    OP_1NEGATE,
    OP_1SUB,
    OP_2,
    OP_2DUP,
    OP_2OVER,
    OP_2ROT,
    OP_2SWAP,
    OP_3,
    OP_4,
    OP_5,
    OP_6,
    OP_7,
    OP_8,
    OP_9,
    OP_10,
    OP_11,
    OP_12,
    OP_13,
    OP_14,
    OP_15,
    OP_16,
    OP_ADD,
    OP_DEPTH,
    OP_DUP,
    OP_EQUALVERIFY,
    OP_MOD,
    OP_OVER,
    OP_PICK,
    OP_ROLL,
    OP_ROT,
    OP_SWAP,
    OP_TUCK,
)

from src.zkscript.types.stack_elements import (
    StackBaseElement,
    StackNumber,
    StackElements,
    StackEllipticCurvePoint,
    StackFiniteFieldElement,
    StackNumber,
)
from src.zkscript.util.utility_functions import bitmask_to_boolean_list, check_order

from src.zkscript.util.utility_functions import bitmask_to_boolean_list, check_order

patterns_to_pick = {
    (0, 1): [OP_DUP],
    (1, 1): [OP_OVER],
    (1, 2): [OP_2DUP],
    (3, 2): [OP_2OVER],
    (3, 4): [OP_2OVER, OP_2OVER],
}
patterns_to_roll = {
    (1, 1): [OP_SWAP],
    (2, 1): [OP_ROT],
    (2, 2): [OP_ROT, OP_ROT],
    (3, 2): [OP_2SWAP],
    (5, 2): [OP_2ROT],
    (5, 4): [OP_2ROT, OP_2ROT],
}
op_range = range(-1, 17)
op_range_to_opcode = {
    -1: OP_1NEGATE,
    0: OP_0,
    1: OP_1,
    2: OP_2,
    3: OP_3,
    4: OP_4,
    5: OP_5,
    6: OP_6,
    7: OP_7,
    8: OP_8,
    9: OP_9,
    10: OP_10,
    11: OP_11,
    12: OP_12,
    13: OP_13,
    14: OP_14,
    15: OP_15,
    16: OP_16,
}


def pick(position: int, n_elements: int) -> Script:
    """Pick the elements x_{position}, ..., x_{position-n_elements}.

    Args:
        position (int): The index of the leftmost element to pick.
        n_elements (int): The number of elements to pick.

    Returns:
        Script to pick elements x_{position}, ..., x_{position-n_elements}.

    Notes:
        {position} is the stack position, so we start counting from 0. If `position < 0`, then we pick from the
            bottom of the stack, which we consider at position -1.

    Example:
        >>> pick(2, 2)
        OP_2 OP_PICK OP_2 OP_PICK
        >>> pick(8, 2)
        OP_8 OP_PICK OP_8 OP_PICK
        >>> pick(1, 2)
        OP_2DUP
        >>> pick(-1, 1)
        OP_DEPTH OP_1SUB OP_PICK
    """
    if position >= 0 and position < n_elements - 1:
        msg = "When positive, position must be at least equal to n_elements - 1: "
        msg += f"position: {position}, n_elements: {n_elements}"
        raise ValueError(msg)

    out = Script()

    if (position, n_elements) in patterns_to_pick:
        out += Script(patterns_to_pick[(position, n_elements)])
    elif position in op_range[1:]:
        out += Script([op_range_to_opcode[position], OP_PICK] * n_elements)
    elif position < 0:
        ix_to_pick = position
        for _ in range(n_elements):
            out += Script.parse_string("OP_DEPTH")
            out += (
                Script.parse_string("OP_1SUB")
                if ix_to_pick == -1
                else nums_to_script([-ix_to_pick]) + Script.parse_string("OP_SUB")
            )
            out += Script.parse_string("OP_PICK")
            ix_to_pick -= 1
    else:
        num_encoded = encode_num(position)
        for _ in range(n_elements):
            out.append_pushdata(num_encoded)
            out += Script([OP_PICK])

    return out


def roll(position: int, n_elements: int) -> Script:
    """Roll the elements x_{position}, .., x_{position-n_elements}.

    Args:
        position (int): The index of the leftmost element to roll.
        n_elements (int): The number of elements to roll.

    Returns:
        Script to roll elements x_{position}, ..., x_{position-n_elements}.

    Notes:
        {position} is the stack position, so we start counting from 0. If `position` < 0, then we roll from the
            bottom of the stack, which we consider at position -1.

    Example:
        >>> roll(2, 2)
        OP_ROT OP_ROT
        >>> roll(8, 2)
        OP_8 OP_ROLL OP_8 OP_ROLL
        >>> roll(1, 1)
        OP_SWAP
        >>> roll(-1, 1)
        OP_DEPTH OP_1SUB OP_ROLL
    """
    if position >= 0 and position < n_elements - 1:
        msg = "When positive, position must be at least equal to n_elements - 1: "
        msg += f"position: {position}, n_elements: {n_elements}"
        raise ValueError(msg)

    if position == n_elements - 1:
        return Script()

    out = Script()

    if (position, n_elements) in patterns_to_roll:
        out += Script(patterns_to_roll[(position, n_elements)])
    elif position in op_range[2:]:
        out += Script([op_range_to_opcode[position], OP_ROLL] * n_elements)
    elif position < 0:
        for _ in range(n_elements):
            out += Script.parse_string("OP_DEPTH")
            out += (
                Script.parse_string("OP_1SUB")
                if position == -1
                else nums_to_script([-position]) + Script.parse_string("OP_SUB")
            )
            out += Script.parse_string("OP_ROLL")
    else:
        num_encoded = encode_num(position)
        for _ in range(n_elements):
            out.append_pushdata(num_encoded)
            out += Script([OP_ROLL])

    return out


def nums_to_script(nums: list[int]) -> Script:
    """Push a list of numbers to the stack.

    Args:
        nums (list[int]): List of numbers to push to the stack.

    Returns:
        Script containing the numbers to push.

    Example:
        >>> nums_to_script([-2, -1, 0, 1, 2, 16, 17, 64, 128])
        0x82 OP_1NEGATE OP_0 OP_1 OP_2 OP_16 0x11 0x40 0x8000
    """
    out = Script()
    for n in nums:
        if n in op_range:
            out += Script([op_range_to_opcode[n]])
        else:
            out.append_pushdata(encode_num(n))

    return out


def mod(
    stack_preparation: str = "OP_FROMALTSTACK OP_ROT",
    is_mod_on_top: bool = True,
    is_positive: bool = True,
    is_constant_reused: bool = True,
) -> Script:
    """Perform modulo operation in Bitcoin Script.

    This function generates a Bitcoin Script that performs a modulo operation. The behavior of the
    operation can be customised using the provided parameters.

    Args:
        stack_preparation (str, optional): Prepare the stack before performing the modulo operation. Defaults to
            `OP_FROMALTSTACK OP_ROT`.
        is_mod_on_top (bool, optional): If `True`, the modulo constant is the one at the top of the stack after the
            stack preparation, else the modulo constant is the second one from the top of the stack. Defaults to `True`.
        is_positive (bool, optional): If `True`, adds operations to ensure the modulo value is positive.
            Defaults to `True`.
        is_constant_reused (bool, optional): If `True`, the modulo constant remains as the second-to-top element on the
            stack after execution. Defaults to `True`.

    Returns:
        A Bitcoin Script that performs the modulo operation based on the specified parameters.

    Examples:
        - The simpler situation is when `is_positive = False`, `stack_preparation = False`,
          and `is_constant_reused = False`.
          In this situation, the script only performs a modulo operation.
            Let `stack_in = [-5, 3]`, and `is_mod_on_top = True`, then `stack_out = [-5%3 = -2]`.
            Let `stack_in = [2, 7]`, and `is_mod_on_top = False`, then `stack_out = [7%2 = 1]`.
        - If we have `is_positive = False`, `stack_preparation = False`, and `is_constant_reused = True`,
          after the modulo operation the modulo constant is still present in the stack.
            Let `stack_in = [-5, 3]`, and `is_mod_on_top = True`, then `stack_out = [3, -2]`.
            Let `stack_in = [2, 7]`, and `is_mod_on_top = False`, then `stack_out = [2, 1]`.
        - If we have `is_positive = True`, `stack_preparation = False`, after taking the modulo the first time we pick a
          positive representative for the modulo.
            Let `stack_in = [-5, 3]`, and `is_mod_on_top = True`, then
            `stack_out = [(3 if is_constant_reused = True), 2]`.
            Let `stack_in = [2, 7]`, and `is_mod_on_top = False`, then
            `stack_out = [(2 if is constant reused = True), 1]`.
        - If `stack_preparation = True`, before starting the modulo operation, a new element is loaded from the
          altstack. The two opcodes added to the script if `stack_preparation = True`, modify the stack as follows:
            Let `stack_in = [1, 2], alt_stack_in = [3]`, after `OP_FROMALTSTACK OP_ROT`, we get:
            `stack_out = [2, 3, 1], alt_stack_out = []`.
    """
    out = Script.parse_string(stack_preparation)

    if is_positive:
        if is_constant_reused:
            if is_mod_on_top:
                out += Script([OP_TUCK, OP_MOD, OP_OVER, OP_ADD, OP_OVER, OP_MOD])
            else:
                out += Script([OP_OVER, OP_MOD, OP_OVER, OP_ADD, OP_OVER, OP_MOD])
        else:  # noqa: PLR5501
            if is_mod_on_top:
                out += Script([OP_TUCK, OP_MOD, OP_OVER, OP_ADD, OP_SWAP, OP_MOD])
            else:
                out += Script([OP_OVER, OP_MOD, OP_OVER, OP_ADD, OP_SWAP, OP_MOD])
    else:  # noqa: PLR5501
        if is_constant_reused:
            if is_mod_on_top:
                out += Script([OP_TUCK, OP_MOD])
            else:
                out += Script([OP_OVER, OP_MOD])
        else:  # noqa: PLR5501
            if is_mod_on_top:
                out += Script([OP_MOD])
            else:
                out += Script([OP_SWAP, OP_MOD])

    return out


def verify_bottom_constant(n: int) -> Script:
    """Verify a constant against a provided value in Bitcoin Script.

    This function generates a Bitcoin Script that checks if a specific constant value is equal to the value present at
    the top of the stack. If the check passes, the script continues; otherwise, it terminates the transaction.

    Args:
        n (int): The constant value to check against.

    Returns:
        A Bitcoin Script that verifies the constant against the value at the bottom of the stack.
    """
    return Script([OP_DEPTH, OP_1SUB, OP_PICK]) + nums_to_script([n]) + Script([OP_EQUALVERIFY])


def move(
    stack_element: StackElements, moving_function: Union[roll, pick], start_index: int = 0, end_index: int | None = None
) -> Script:
    """Return the script that moves stack_element[start_index], ..., stack_element[end_index-1] with moving_function."""
    length = (
        1
        if not isinstance(stack_element, (StackFiniteFieldElement, StackEllipticCurvePoint))
        else 2 * stack_element.x.extension_degree
        if isinstance(stack_element, StackEllipticCurvePoint)
        else stack_element.extension_degree
    )
    if end_index is None:
        end_index = length
    if start_index < 0:
        msg = "Start index must be positive: "
        msg += f"start_index {start_index}"
        raise ValueError(msg)
    if length < end_index:
        msg = "Moving more elements than self: "
        msg += f"Self has {length} elements, end_index: {end_index}"
        raise ValueError(msg)
    return moving_function(position=stack_element.position - start_index, n_elements=end_index - start_index)


def bool_to_moving_function(is_rolled: bool) -> Union[pick, roll]:
    """Map is_rolled (bool) to corresponding moving function."""
    return roll if is_rolled else pick


def reverse_endianness_fixed_length(
    length: int,
    stack_element: StackBaseElement = StackBaseElement(0),  # noqa: B008
    rolling_option: bool = True,
) -> Script:
    """Reverse the endianness of a StackBaseElement of byte length `length`.

    Args:
        length (int): The byte length of stack_element.
        stack_element (StackBaseElement): The stack element whose endianness should be reversed.
            Defaults to `StackBaseElement(0)`.
        rolling_option (bool): Whether stack_element should be rolled. Defaults to `True`.

    """
    out = move(stack_element, roll if rolling_option else pick)  # Move stack_element
    out += Script.parse_string(" ".join(["OP_1 OP_SPLIT"] * (length - 1)))
    out += Script.parse_string(" ".join(["OP_SWAP OP_CAT"] * (length - 1)))
    return out


def reverse_endianness_bounded_length(
    max_length: int,
    stack_element: StackBaseElement = StackBaseElement(0),  # noqa: B008
    rolling_option: bool = True,
) -> Script:
    """Reverse the endianness of a StackBaseElement of byte length at most `max_length`.

    Args:
        max_length (int): The maximum byte length of stack_element.
        stack_element (StackBaseElement): The stack element whose endianness should be reversed.
            Defaults to `StackBaseElement(0)`.
        rolling_option (bool): Whether stack_element should be rolled. Defaults to `True`.

    """
    out = move(stack_element, roll if rolling_option else pick)  # Move stack_element

    # stack in: [.., stack_element, .., stack_element]
    # stack out: [.., stack_element, .., len(stack_element), right_padded(stack_element,max_length)]
    out += Script.parse_string("OP_SIZE OP_SWAP")
    out += Script.parse_string("0x00 OP_CAT")
    out += nums_to_script([max_length + 1])
    out += Script.parse_string("OP_NUM2BIN")

    # stack in:  [.., stack_element, .., len(stack_element), right_padded(stack_element,max_length)]
    # stack out: [.., stack_element, .., reverse_endianness(stack_element)
    out += reverse_endianness_fixed_length(max_length + 1)
    out += nums_to_script([max_length + 1])
    out += Script.parse_string(
        "OP_ROT OP_SUB OP_SPLIT OP_NIP"
    )  # Reset reverse_endianness(stack_element) to its correct length
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

    # stack out: [.., int_sig, group_order]
    if [int_sig.position, group_order.position] == [1, 0]:
        out = Script()
    elif [int_sig.position, group_order.position] == [0, 1]:
        out = Script.parse_string("OP_SWAP" if all([is_group_order_rolled, is_int_sig_rolled]) else "OP_2DUP OP_SWAP")
    else:
        if group_order.position >= 0:
            check_order([group_order, int_sig])
        out = move(int_sig, bool_to_moving_function(is_int_sig_rolled))  # Move int_sig
        out += move(
            group_order.shift(1 - is_int_sig_rolled if group_order.position >= 0 else 0),
            bool_to_moving_function(is_group_order_rolled),
        )  # Move group_order

    # stack out: [.., int_sig, group_order, int_sig, group_order]
    out += Script.parse_string("OP_2DUP")

    # Put int_sig in canonical form
    # stack out: [.., min{int_sig, group_order - int_sig}]
    out += Script.parse_string("OP_2 OP_DIV OP_GREATERTHAN OP_IF OP_SWAP OP_SUB OP_ELSE OP_DROP OP_ENDIF")

    # Reverse endianness of min{int_sig, group_order - int_sig}
    # stack out: [.., s]
    out += reverse_endianness_bounded_length(max_length=32)

    if add_prefix:
        out += Script.parse_string("OP_SIZE OP_SWAP OP_CAT")  # Compute len(s)||s
        out += Script.parse_string("OP_2 OP_SWAP OP_CAT")  # Compute 02||len(s)||s

    return out


def bytes_to_unsigned(
    length_stack_element: int,
    stack_element: StackBaseElement = StackBaseElement(0),  # noqa: B008
    rolling_option: bool = True,
) -> Script:
    """Convert a bytestring of length `length` to an unsigned integer.

    Stack input:
        - stack: [.., stack_element, ..]
    Stack output:
        - stack: [.., stack_element, .., n] where `n` is `reverse_endianness(stack_element)` if the MSB of
            `stack_element` is less than 0x80, else `reverse_endianness(stack_element)||00`

    Args:
        stack_element (StackBaseElement): The bytestring to convert into a number
        length_stack_element: int: The length of the stack element
        rolling_option (bool): If `True`, stack_element is removed from the stack. Defaults to `True`.

    Returns:
        The script that converts `stack_element` into an unsigned number.
    """
    return reverse_endianness_fixed_length(
        length=length_stack_element, stack_element=stack_element, rolling_option=rolling_option
    ) + Script.parse_string("0x00 OP_CAT OP_BIN2NUM")


def enforce_mul_equal(
    clean_constant: bool = False,
    is_constant_reused: bool = False,
    modulus: StackNumber = StackNumber(-1,False),
    a: StackFiniteFieldElement = StackFiniteFieldElement(2,False,1),
    b: StackFiniteFieldElement = StackFiniteFieldElement(1,False,1),
    c: StackFiniteFieldElement = StackFiniteFieldElement(0,False,1),
    rolling_options: int = 7,
    leave_on_top_of_stack: int = 0,
    equation_to_check: int = 1
) -> Script:
    """Enforce that a = b*c % modulus.

    Stack input:
        - stack:    [.., modulus, .., a, .., b, .., c, ..]
        - altstack: []
    Stack output:
        - stack:    [.., modulus, .., a, .., b, .., c, .., ?] or fail
        - altstack: []

    Args:
        clean_constant (bool): Whether the modulus should be cleaned from the stack or not.
        is_constant_reused (bool): Whether the modulus should be left on top of the or not.
            Defaults to `False`.
        modulus (StackNumber): the position of the modulus used to check the equality. Defaults to
            `StackNumber(-1,False)`.
        a (StackFiniteFieldElement): the element a for which a = b*c % modulus. Defaults to
            `StackFiniteFieldElement(2,False,1)`
        b (StackFiniteFieldElement): the element b for which a = b*c % modulus. Defaults to
            `StackFiniteFieldElement(1,False,1)`
        c (StackFiniteFieldElement): the element c for which a = b*c % modulus. Defaults to
            `StackFiniteFieldElement(0,False,1)`
        rolling_options (int): Whether to roll the elements. Defaults to `7`, roll everything.
        leave_on_top_of_stack (int): Whether to leave the elements a,b,c on top of the stack after the
            equality check. Defaults to `0`, don't leave anything.
        equation_to_check (int): Which equation to check:
            - 1 << 0: a = b*c % modulus
            - 1 << 1: c = a*b % modulus
            - 1 << 2: b = a*c % modulus
    """
    if modulus.position != -1:
        check_order([modulus,a,b,c])
    list_rolling_options = bitmask_to_boolean_list(rolling_options, 3)
    list_leave_on_top = bitmask_to_boolean_list(leave_on_top_of_stack, 3)

    out = move(a,bool_to_moving_function(list_rolling_options[0]))
    if list_leave_on_top[0]:
        out += Script.parse_string("OP_DUP")
    out += move(b.shift(1 + list_leave_on_top[0]),bool_to_moving_function(list_rolling_options[1]))
    if list_leave_on_top[1]:
        out += Script.parse_string("OP_TUCK")
    if equation_to_check >> 1 & 1:
        out += Script.parse_string("OP_MUL")
    out += move(
        c.shift(2 + list_leave_on_top[0] + list_leave_on_top[1] - (equation_to_check >> 1 & 1)),
        bool_to_moving_function(list_rolling_options[2])
        )
    if list_leave_on_top[2]:
        out += Script.parse_string("OP_TUCK")
    if equation_to_check >> 2 & 1:
        out += roll(position=2 + list_leave_on_top[2],n_elements=1) # roll a
    if not (equation_to_check >> 1 & 1):
        out += Script.parse_string("OP_MUL")
    if list_leave_on_top[2]:
        out += Script.parse_string("OP_ROT")
    out += Script.parse_string("OP_SUB")
    out += move(
        modulus.shift(
            3\
                + list_leave_on_top[0]\
                    + list_leave_on_top[1]\
                        + list_leave_on_top[2]\
                            - list_rolling_options[0]\
                                - list_rolling_options[1]\
                                    - list_rolling_options[2]\
                                        if modulus.position > 0 else 0
            ),
        bool_to_moving_function(clean_constant)
        )
    out += mod("",is_constant_reused=is_constant_reused)
    out += Script.parse_string("OP_0 OP_EQUALVERIFY")

    return out

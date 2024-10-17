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
op_range_to_opccode = {
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
    """Pick the elements x_{position}, .., x_{position-n_elements}.

    `position` is the stack position, so we start counting from 0. If `position < 0`, then we pick
    from the bottom of the stack, which we consider at position -1.

    Example:
        `n_elements` = 2, `position` = 2 --> OP_2 OP_PICK OP_2 OP_PICK
        `n_elements` = 2, `position` = 8 --> OP_8 OP_PICK OP_8 OP_PICK
        `n_elements` = 2, `position` = 1 --> OP_2DUP
        `n_elements` = 1, `position` = -1 --> OP_DEPTH OP_1SUB OP_PICK

    """
    if position >= 0 and position < n_elements - 1:
        msg = f"When positive, position must be at least equal to n_elements - 1:\
            position {position}, n_elements: {n_elements}"
        raise ValueError(msg)

    out = Script()

    if (position, n_elements) in patterns_to_pick:
        out += Script(patterns_to_pick[(position, n_elements)])
    elif position in op_range[1:]:
        out += Script([op_range_to_opccode[position], OP_PICK] * n_elements)
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

    `position` is the stack position, so we start counting from 0. If `position` < 0, then we roll
    from the bottom of the stack, which we consider at position -1.

    Example:
        `n_elements` = 2, `position` = 2 --> OP_2 OP_PICK OP_2 OP_PICK
        `n_elements` = 2, `position` = 8 --> OP_8 OP_PICK OP_8 OP_PICK
        `n_elements` = 1, `position` = 1 --> OP_SWAP
        `n_elements` = 1, `position` = -1 --> OP_DEPTH OP_1SUB OP_ROLL

    """
    if position >= 0 and position < n_elements - 1:
        msg = f"When positive, position must be at least equal to n_elements - 1:\
            position {position}, n_elements: {n_elements}"
        raise ValueError(msg)

    if position == n_elements - 1:
        return Script()

    out = Script()

    if (position, n_elements) in patterns_to_roll:
        out += Script(patterns_to_roll[(position, n_elements)])
    elif position in op_range[2:]:
        out += Script([op_range_to_opccode[position], OP_ROLL] * n_elements)
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
    """Take a list of number and return the script pushing those numbers to the stack."""
    out = Script()
    for n in nums:
        if n in op_range:
            out += Script([op_range_to_opccode[n]])
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
        stack_preparation (`str`, optional): Prepare the stack before performing the modulo operation. Defaults to
        `OP_FROMALTSTACK OP_ROT`.
        is_mod_on_top (`bool`, optional): If `True`, the modulo constant is the one at the top of the stack after the
            stack preparation, else the modulo constant is the second one from the top of the stack. Defaults to `True`.
        is_positive (`bool`, optional): If `True`, adds operations to ensure the modulo value is positive.
            Defaults to `True`.
        is_constant_reused (`bool`, optional): If `True`, modifies the script to leave the modulo constant on the stack.
            Defaults to `True`.

    Returns:
        A Bitcoin Script that performs the modulo operation based on the specified parameters.

    Examples:
        - The simpler situation is when `is_positive = False`, `stack_preparation = False`, and `is_constant_reused = False`.
          In this situation, the script only performs a modulo operation.
            Let `stack_in = [-5, 3]`, and `is_mod_on_top = True`, then `stack_out = [-5%3 = -2]`.
            Let `stack_in = [2, 7]`, and `is_mod_on_top = False`, then `stack_out = [7%2 = 1]`.
        - If we have `is_positive = False`, `stack_preparation = False`, and `is_constant_resued = True`, after the modulo
          operation the modulo constant is still present in the stack.
            Let `stack_in = [-5, 3]`, and `is_mod_on_top = True`, then `stack_out = [3, -2]`.
            Let `stack_in = [2, 7]`, and `is_mod_on_top = False`, then `stack_out = [2, 1]`.
        - If we have `is_positive = True`, `stack_preparation = False`, after taking the modulo the first time we pick a
          positive representative for the modulo.
            Let `stack_in = [-5, 3]`, and `is_mod_on_top = True`, then
            `stack_out = [(3 if is_constant_reused = True), 2]`.
            Let `stack_in = [2, 7]`, and `is_mod_on_top = False`, then
            `stack_out = [(2 if is constant reused = True), 1]`.
        - If `stack_preparation = True`, before starting the modulo operation, a new element is loaded from the alt stack.
          The two opcodes added to the script if `stack_preparation = True`, modify the stack as follows:
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
        n (`int`): The constant value to check against.

    Returns:
        A Bitcoin Script that verifies the constant against the value at the bottom of the stack.

    """
    return Script([OP_DEPTH, OP_1SUB, OP_PICK]) + nums_to_script([n]) + Script([OP_EQUALVERIFY])

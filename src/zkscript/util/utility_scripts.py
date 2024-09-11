from tx_engine import Script, encode_num
from tx_engine.engine.op_codes import (
    OP_0,
    OP_1,
    OP_1NEGATE,
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
    OP_DUP,
    OP_OVER,
    OP_PICK,
    OP_ROLL,
    OP_ROT,
    OP_SWAP,
)

patterns_to_pick = {(0, 1): [OP_DUP], (1, 1): [OP_OVER], (1, 2): [OP_2DUP], (3, 2): [OP_2OVER]}
patterns_to_roll = {
    (1, 1): [OP_SWAP],
    (2, 1): [OP_ROT],
    (2, 2): [OP_ROT, OP_ROT],
    (3, 2): [OP_2SWAP],
    (5, 2): [OP_2ROT],
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

    {position} is the stack position, so we start counting from 0.

    Example:
        n_elements = 2, position = 2 --> OP_2 OP_PICK OP_2 OP_PICK
        n_elements = 2, position = 8 --> OP_8 OP_PICK OP_8 OP_PICK
        n_elements = 2, position = 1 --> OP_2DUP

    """
    out = Script()

    if (position, n_elements) in patterns_to_pick:
        out += Script(patterns_to_pick[(position, n_elements)])
    elif position in op_range:
        out += Script([op_range_to_opccode[position], OP_PICK] * n_elements)
    else:
        num_encoded = encode_num(position)
        for _i in range(n_elements):
            out.append_pushdata(num_encoded)
            out += Script([OP_PICK])

    return out


def roll(position: int, n_elements: int) -> Script:
    """Pick the elements x_{position}, .., x_{position-n_elements}.

    Position is the stack position, so we start counting from 0.

    Example:
        n_elements = 2, position = 2 --> OP_2 OP_PICK OP_2 OP_PICK
        n_elements = 2, position = 8 --> OP_8 OP_PICK OP_8 OP_PICK
        n_elements = 1, position = 1 --> OP_SWAP

    """
    out = Script()

    if (position, n_elements) in patterns_to_roll:
        out += Script(patterns_to_roll[(position, n_elements)])
    elif position in op_range:
        out += Script([op_range_to_opccode[position], OP_ROLL] * n_elements)
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

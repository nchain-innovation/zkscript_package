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


def pick(position: int, nElements: int) -> Script:
    """Pick nElements starting from position.

    Position is the stack position, so we star counting from 0.

    Example:
        nElements = 2, position = 2 --> OP_2 OP_PICK OP_2 OP_PICK

    """
    out = Script()

    if (position, nElements) in patterns_to_pick:
        out += Script(patterns_to_pick[(position, nElements)])
    elif position in op_range:
        out += Script([op_range_to_opccode[position], OP_PICK] * nElements)
    else:
        num_encoded = encode_num(position)
        for _i in range(nElements):
            out.append_pushdata(num_encoded)
            out += Script([OP_PICK])

    return out


def roll(position: int, nElements: int) -> Script:
    """Roll nElements starting from position.

    Position is the stack position, so we star counting from 0.

    Example:
        nElements = 2, position = 2 --> OP_2 OP_ROLL OP_2 OP_ROLL

    """
    out = Script()

    if (position, nElements) in patterns_to_roll:
        out += Script(patterns_to_roll[(position, nElements)])
    elif position in op_range:
        out += Script([op_range_to_opccode[position], OP_ROLL] * nElements)
    else:
        num_encoded = encode_num(position)
        for _i in range(nElements):
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

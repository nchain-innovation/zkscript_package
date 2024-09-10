from tx_engine import Script, encode_num


def pick(position: int, nElements: int) -> Script:
    """Pick nElements starting from position.

    Position is the stack position, so we star counting from 0.

    Example:
        nElements = 2, position = 2 --> OP_2 OP_PICK OP_2 OP_PICK

    """
    if position < 17:
        return Script.parse_string(" ".join([str(position), "OP_PICK"] * nElements))
    return Script.parse_string(" ".join(["0x" + encode_num(position).hex(), "OP_PICK"] * nElements))


def roll(position: int, nElements: int) -> Script:
    """Roll nElements starting from position.

    Position is the stack position, so we star counting from 0.

    Example:
        nElements = 2, position = 2 --> OP_2 OP_ROLL OP_2 OP_ROLL

    """
    if position < 17:
        return Script.parse_string(" ".join([str(position), "OP_ROLL"] * nElements))
    return Script.parse_string(" ".join(["0x" + encode_num(position).hex(), "OP_ROLL"] * nElements))


def nums_to_script(nums: list[int]) -> Script:
    """Take a list of number and return the script pushing those numbers to the stack."""
    out = Script()
    for n in nums:
        if n == -1:
            out += Script.parse_string("-1")
        elif 0 <= n <= 16:
            out += Script.parse_string(str(n))
        else:
            out.append_pushdata(encode_num(n))

    return out

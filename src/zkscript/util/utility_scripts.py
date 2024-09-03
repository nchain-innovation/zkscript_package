from tx_engine import Script, encode_num


def pick(position: int, nElements: int) -> Script:
    """Pick nElements starting from position.

    Position is the stack position, so we star counting from 0.

    Example:
        nElements = 2, position = 2 --> OP_2 OP_PICK OP_2 OP_PICK

    """
    out = Script()

    if position == 0 and nElements == 1:
        out += Script.parse_string('OP_DUP')
    elif position == 1 and nElements == 1:
        out += Script.parse_string('OP_OVER')
    elif position == 1 and nElements == 2:
        out += Script.parse_string('OP_2DUP')
    elif position == 3 and nElements == 2:
        out += Script.parse_string('OP_2OVER')
    elif position < 17:
        out += Script.parse_string(' '.join([str(position), 'OP_PICK'] * nElements))
    else:
        num_encoded = encode_num(position)
        for i in range(nElements):
            out.append_pushdata(num_encoded)
            out += Script.parse_string('OP_PICK')
    
    return out

def roll(position: int, nElements: int) -> Script:
    """Roll nElements starting from position.

    Position is the stack position, so we star counting from 0.

    Example:
        nElements = 2, position = 2 --> OP_2 OP_ROLL OP_2 OP_ROLL

    """
    out = Script()

    if position == 1 and nElements == 1:
        out += Script.parse_string('OP_SWAP')
    elif position == 2 and nElements == 1:
        out += Script.parse_string('OP_ROT')
    elif position == 2 and nElements == 2:
        out += Script.parse_string('OP_ROT OP_ROT')
    elif position == 3 and nElements == 2:
        out += Script.parse_string('OP_2SWAP')
    elif position == 5 and nElements == 2:
        out += Script.parse_string('OP_2ROT')
    elif position < 17:
        out += Script.parse_string(' '.join([str(position), 'OP_ROLL'] * nElements))
    else:
        num_encoded = encode_num(position)
        for i in range(nElements):
            out.append_pushdata(num_encoded)
            out += Script.parse_string('OP_ROLL')

    return out

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

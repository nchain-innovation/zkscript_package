from tx_engine import Script


def optimise_script(script: Script) -> Script:
    """Optimise a script by removing redundant operations from and to the altstack.

    This function removes pairs of redundant operations, such as `OP_TOALTSTACK OP_FROMALTSTACK` and
    `OP_FROMALTSTACK OP_TOALTSTACK`, which cancel each other out. The function iterates over the script
    until no further redundant operations can be removed.

    Args:
        script (Script): The script to be optimised.

    Returns:
        The optimised script with redundant operations removed.

    """
    patterns = [
        ["OP_TOALTSTACK", "OP_FROMALTSTACK"],
        ["OP_FROMALTSTACK", "OP_TOALTSTACK"],
        ["OP_ROT", "OP_ROT", "OP_ROT"],
    ]

    script_list = script.to_string().split()
    stack = []

    for op in script_list:
        stack.append(op)

        for pattern in patterns:
            pattern_length = len(pattern)

            if len(stack) >= pattern_length:
                last_elements = stack[-pattern_length:]

                if last_elements == pattern:
                    for _ in range(pattern_length):
                        stack.pop()
                    break

    return Script.parse_string(" ".join(stack))

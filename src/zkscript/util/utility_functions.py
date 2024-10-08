from tx_engine import Script


def optimise_script(script: Script) -> Script:
    """Optimize a script by removing redundant operations from and to the altstack.

    This function removes pairs of redundant operations, such as `OP_TOALTSTACK OP_FROMALTSTACK` and
    `OP_FROMALTSTACK OP_TOALTSTACK`, hich cancel each other out. The function iterates over the script
    until no further redundant operations can be removed.

    Args:
        script (Script): The script to be optimized.

    Returns:
        Script: The optimized script with redundant operations removed.

    """
    patterns = ["OP_TOALTSTACK OP_FROMALTSTACK", "OP_FROMALTSTACK OP_TOALTSTACK"]

    optimised_script = script.to_string()
    for pattern in patterns:
        while pattern in optimised_script:
            optimised_script = optimised_script.replace(pattern, "")

    return Script.parse_string(optimised_script)

from tx_engine import Script


def optimise_script(script: Script) -> Script:
    """Optimise a script by removing redundant operations."""
    patterns = ["OP_TOALTSTACK OP_FROMALTSTACK", "OP_FROMALTSTACK OP_TOALTSTACK"]

    optimise_script = script.to_string()
    for pattern in patterns:
        optimised_script = optimise_script.replace(pattern, "")

    return Script.parse_string(optimised_script)

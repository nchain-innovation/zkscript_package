"""Utility functions."""

from typing import Union

from tx_engine import Script

from src.zkscript.types.stack_elements import StackElements


def optimise_script(script: Script) -> Script:
    """Optimise a script by simplifying certain operations.

    This function simplifies certain operations, such as `OP_TOALTSTACK OP_FROMALTSTACK` and
    `OP_FROMALTSTACK OP_TOALTSTACK`, which cancel each other out and are therefore removed.
    The function iterates over the script until no further operations can be simplified.

    Args:
        script (Script): The script to be optimised.

    Returns:
        The optimised script with redundant operations removed.
    """
    patterns = {
        (
            "OP_TOALTSTACK",
            "OP_FROMALTSTACK",
        ): [],
        (
            "OP_FROMALTSTACK",
            "OP_TOALTSTACK",
        ): [],
        (
            "OP_ROT",
            "OP_ROT",
            "OP_ROT",
        ): [],
        (
            "OP_SWAP",
            "OP_ADD",
        ): ["OP_ADD"],
        (
            "OP_SWAP",
            "OP_MUL",
        ): ["OP_MUL"],
        (
            "OP_SWAP",
            "OP_SUB",
            "OP_NEGATE",
        ): ["OP_SUB"],
    }

    script_list = script.to_string().split()
    stack = []

    for op in script_list:
        stack.append(op)

        for pattern, replacement in patterns.items():
            pattern_length = len(pattern)

            if len(stack) >= pattern_length:
                last_elements = tuple(stack[-pattern_length:])

                if last_elements == pattern:
                    for _ in range(pattern_length):
                        stack.pop()
                    stack.extend(replacement)
                    break

    return Script.parse_string(" ".join(stack))


def check_order(stack_elements: list[StackElements]) -> ValueError | None:
    """Check that the elements in `stack_elements` do not overlap and are in the right order.

    The function returns `True` if:
        - stack_elements[i].overlaps_on_the_right(stack_elements[i+1]) is `False` for every i
        - stack_elements[i].is_before(stack_elements[i+1]) is `True` for every i

    Args:
        stack_elements (list[StackElements]): The list of stack elements to be checked
    """
    for i in range(len(stack_elements) - 1):
        overlaps, msg = stack_elements[i].overlaps_on_the_right(stack_elements[i + 1])
        if overlaps:
            msg = f"{msg}\nIndex of self: {i}, index of other: {i+1}"
            raise ValueError(msg)
    for i in range(len(stack_elements) - 1):
        if not stack_elements[i].is_before(stack_elements[i + 1]):
            msg = f"Elements {i}: {stack_elements[i]} is not before element {i+1}: {stack_elements[i+1]}"
            raise ValueError(msg)

    return


def boolean_list_to_bitmask(boolean_list: list[bool]) -> int:
    """Convert a list of True, False into a bitmask.

    Example:
        >>> boolean_list_to_bitmask([True])
        1
        >>> boolean_list_to_bitmask([True,False])
        1
        >>> boolean_list_to_bitmask([False,True])
        2
        >>> boolean_list_to_bitmask([True,True])
        3
    """
    bitmask = 0
    for ix, option in enumerate(boolean_list):
        bitmask |= 1 << ix if option else 0
    return bitmask


def bitmask_to_boolean_list(bitmask: int, list_length: int) -> list[bool]:
    """Convert a bitmask to a list of True, False of length list_length.

    Example:
        >>> bitmask_to_boolean_list(1,1)
        [True]
        >>> bitmask_to_boolean_list(1,2)
        [True, False]
        >>> bitmask_to_boolean_list(2,2)
        [False, True]
        >>> bitmask_to_boolean_list(3,2)
        [True, True]
    """
    out = []
    while bitmask > 0:
        out.append(bool(bitmask & 1))
        bitmask = bitmask >> 1
    return [*out, *[False] * (list_length - len(out))]


def base_function_size_estimation_miller_loop(
    modulus: int,
    modulo_threshold: int,
    ix: int,
    n: int,
    exp_miller_loop: list[int],
    current_size_miller_output: int,
    current_size_point_multiplication: int,
    is_triple_miller_loop: bool,
) -> Union[bool, int]:
    """Estimate size of elements computed while executing the Miller loop.

    Args:
        modulus (int): the modulus of BLS12-381.
        modulo_threshold (int): the size after which to take a modulo in the script (in bytes).
        ix (int): the index of the Miller loop.
        n (int): integer constant for which |bit_size(ab)| <= |bit_size(a)| + |bit_size(b)| + n
        exp_miller_loop (list[int]): the binary expansion of the value for which the Miller loop is computed.
        current_size_miller_output (int): the current size of the Miller output.
        current_size_point_multiplication (int): the current size of the calculation of w*Q, where w is the
            value over which the Miller loop is computed.
        is_triple_miller_loop (bool): whether the function is used to estimate the sizes for the triple Miller
            loop or a single one.

    Returns:
        take_modulo_miller_loop_output (bool): whether to take a modulo after the update of the Miller loop
            output.
        take_modulo_point_multiplication (bool): whether to take a modulo after the update of the intermediate
            value of w*Q.
        out_size_miller_loop (int): the new size of the Miller loop output (in bytes).
        out_size_point_miller_loop (int): the new size of the intermediate value of w*Q (in bytes).
    """
    if ix == 0:
        return True, True, 0, 0

    if exp_miller_loop[ix - 1] == 0:
        multiplier = 3 if is_triple_miller_loop else 1
        # Next iteration update will be: f <-- f^2 * line_eval, T <-- 2T
        future_size_miller_output = current_size_miller_output
        future_size_miller_output = 2 * future_size_miller_output + n
        for _ in range(multiplier):
            future_size_miller_output = modulus.bit_length() + future_size_miller_output + n
        future_size_point_multiplication = modulus.bit_length() + current_size_point_multiplication + (6).bit_length()
    else:
        multiplier = 6 if is_triple_miller_loop else 2
        # Next iteration update will be: f <-- f^2 * line_eval * line_eval, T <-- 2T ± Q
        future_size_miller_output = current_size_miller_output
        future_size_miller_output = 2 * future_size_miller_output + n
        for _ in range(multiplier):
            future_size_miller_output = modulus.bit_length() + future_size_miller_output + n
        future_size_point_multiplication = modulus.bit_length() + current_size_point_multiplication + (6).bit_length()
        future_size_point_multiplication = modulus.bit_length() + future_size_point_multiplication + (6).bit_length()

    if future_size_miller_output > modulo_threshold:
        take_modulo_miller_loop_output = True
        out_size_miller_loop = modulus.bit_length()
    else:
        take_modulo_miller_loop_output = False
        out_size_miller_loop = future_size_miller_output

    if future_size_point_multiplication > modulo_threshold:
        take_modulo_point_multiplication = True
        out_size_point_miller_loop = modulus.bit_length()
    else:
        take_modulo_point_multiplication = False
        out_size_point_miller_loop = future_size_point_multiplication

    return (
        take_modulo_miller_loop_output,
        take_modulo_point_multiplication,
        out_size_miller_loop,
        out_size_point_miller_loop,
    )

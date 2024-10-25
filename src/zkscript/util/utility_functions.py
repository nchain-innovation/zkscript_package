from typing import List, Union

from tx_engine import Script

from src.zkscript.types.stack_elements import StackElements
from src.zkscript.util.utility_scripts import pick, roll


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


def boolean_list_to_bitmask(boolean_list: List[bool]) -> int:
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


def bitmask_to_boolean_list(bitmask: int, list_length: int) -> List[bool]:
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


def bool_to_moving_function(is_rolled: bool) -> Union[pick, roll]:
    """Map is_rolled (bool) to correspoding moving function."""
    return roll if is_rolled else pick

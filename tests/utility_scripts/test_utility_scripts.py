import pytest
from tx_engine import Context, Script

from src.zkscript.types.stack_elements import StackBaseElement, StackNumber
from src.zkscript.util.utility_scripts import (
    mod,
    move,
    nums_to_script,
    pick,
    reverse_endianness,
    roll,
    verify_bottom_constant,
)


def generate_verify(z) -> Script:
    out = Script()
    for ix, el in enumerate(z[::-1]):
        out += nums_to_script([el])
        if ix != len(z) - 1:
            out += Script.parse_string("OP_EQUALVERIFY")
        else:
            out += Script.parse_string("OP_EQUAL")

    return out


@pytest.mark.parametrize(
    ("position", "n_elements", "stack", "expected"),
    [
        (1, 1, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]),
        (2, 1, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 8, 9, 7]),
        (2, 2, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 9, 7, 8]),
        (3, 2, list(range(10)), [0, 1, 2, 3, 4, 5, 8, 9, 6, 7]),
        (5, 2, list(range(10)), [0, 1, 2, 3, 6, 7, 8, 9, 4, 5]),
        (5, 4, list(range(10)), [0, 1, 2, 3, 8, 9, 4, 5, 6, 7]),
        (
            10,
            3,
            list(range(20)),
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 18, 19, 9, 10, 11],
        ),
        (4, 5, list(range(10)), list(range(10))),
        (9, 10, list(range(20)), list(range(20))),
        (1, 2, list(range(10)), list(range(10))),
        (-1, 1, list(range(10)), [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]),
        (-1, 2, list(range(10)), [2, 3, 4, 5, 6, 7, 8, 9, 0, 1]),
        (-2, 2, list(range(10)), [0, 3, 4, 5, 6, 7, 8, 9, 1, 2]),
    ],
)
def test_roll(position, n_elements, stack, expected):
    unlock = nums_to_script(stack)

    lock = roll(position, n_elements)
    lock += generate_verify(expected)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0


@pytest.mark.parametrize(
    ("position", "n_elements", "stack", "expected"),
    [
        (0, 1, list(range(10)), [*list(range(10)), 9]),
        (1, 1, list(range(10)), [*list(range(10)), 8]),
        (1, 2, list(range(10)), [*list(range(10)), 8, 9]),
        (3, 2, list(range(10)), [*list(range(10)), 6, 7]),
        (3, 4, list(range(10)), [*list(range(10)), 6, 7, 8, 9]),
        (10, 3, list(range(20)), [*list(range(20)), 9, 10, 11]),
        (-1, 1, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0]),
        (-1, 2, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1]),
        (-2, 2, list(range(10)), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2]),
    ],
)
def test_pick(position, n_elements, stack, expected):
    unlock = nums_to_script(stack)

    lock = pick(position, n_elements)
    lock += generate_verify(expected)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0


@pytest.mark.parametrize(("position", "n_elements"), [(1, 3), (10, 12), (10, 15)])
@pytest.mark.parametrize("function", [pick, roll])
def test_errors_pick_and_roll(position, n_elements, function):
    msg = r"When positive, position must be at least equal to n_elements - 1: "
    msg += r"position: \d+, n_elements: \d+"
    with pytest.raises(ValueError, match=msg):
        function(position, n_elements)


@pytest.mark.parametrize(
    ("stack_preparation", "is_mod_on_top", "is_constant_reused", "is_positive", "stack", "altstack", "expected"),
    [
        ("", False, False, False, [5, -7], [], [-2]),
        ("", False, False, True, [5, -7], [], [3]),
        ("", False, True, False, [5, -7], [], [5, -2]),
        ("", False, True, True, [5, -7], [], [5, 3]),
        ("", True, False, False, [-7, 5], [], [-2]),
        ("", True, False, True, [-7, 5], [], [3]),
        ("", True, True, False, [-7, 5], [], [5, -2]),
        ("", True, True, True, [-7, 5], [], [5, 3]),
        ("OP_FROMALTSTACK OP_ROT", False, False, False, [-7, 3], [5], [3, -2]),
        ("OP_FROMALTSTACK OP_ROT", False, False, True, [-7, 3], [5], [3, 3]),
        ("OP_FROMALTSTACK OP_ROT", False, True, False, [-7, 3], [5], [3, 5, -2]),
        ("OP_FROMALTSTACK OP_ROT", False, True, True, [-7, 3], [5], [3, 5, 3]),
        ("OP_FROMALTSTACK OP_ROT", True, False, False, [5, 3], [-7], [3, -2]),
        ("OP_FROMALTSTACK OP_ROT", True, False, True, [5, 3], [-7], [3, 3]),
        ("OP_FROMALTSTACK OP_ROT", True, True, False, [5, 3], [-7], [3, 5, -2]),
        ("OP_FROMALTSTACK OP_ROT", True, True, True, [5, 3], [-7], [3, 5, 3]),
        ("", False, False, False, [13, -17], [], [-4]),
        ("", False, False, True, [13, -17], [], [9]),
        ("", False, True, False, [13, -17], [], [13, -4]),
        ("", False, True, True, [13, -17], [], [13, 9]),
        ("", True, False, False, [-17, 13], [], [-4]),
        ("", True, False, True, [-17, 13], [], [9]),
        ("", True, True, False, [-17, 13], [], [13, -4]),
        ("", True, True, True, [-17, 13], [], [13, 9]),
    ],
)
def test_mod(stack_preparation, is_mod_on_top, is_positive, is_constant_reused, stack, altstack, expected):
    unlock = nums_to_script(stack)
    lock = nums_to_script(altstack)
    lock += Script.parse_string("OP_TOALTSTACK" * len(altstack))

    lock += mod(
        stack_preparation=stack_preparation,
        is_mod_on_top=is_mod_on_top,
        is_positive=is_positive,
        is_constant_reused=is_constant_reused,
    )
    lock += generate_verify(expected)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0


@pytest.mark.parametrize(
    ("n", "stack"),
    [
        (0, [0, 1]),
        (1, [1, 0, 0]),
        (-10, [-10, 0, 0]),
        (100, [100] + [0] * 100),
    ],
)
def test_verify_bottom_constant(n, stack):
    unlock = nums_to_script(stack)

    lock = verify_bottom_constant(n=n)
    lock += generate_verify(stack)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0


@pytest.mark.parametrize(
    ("n", "stack"),
    [
        (0, []),
        (1, [2, 0]),
    ],
)
def test_fail_verify_bottom_constant(n, stack):
    unlock = nums_to_script(stack)

    lock = verify_bottom_constant(n=n)
    context = Context(script=unlock + lock)

    assert not context.evaluate()


@pytest.mark.parametrize(
    ("stack_element", "moving_function", "start_index", "end_index", "msg"),
    [
        (StackNumber(1, False), roll, 0, 2, r"Moving more elements than self: Self has \d+ elements, end_index: \d+"),
        (StackNumber(1, False), roll, -1, 2, r"Start index must be positive: start_index -\d+"),
        (StackNumber(1, False), roll, -1, 1, r"Start index must be positive: start_index -\d+"),
    ],
)
def test_errors_move(stack_element, moving_function, start_index, end_index, msg):
    with pytest.raises(ValueError, match=msg):
        move(stack_element, moving_function, start_index, end_index)


@pytest.mark.parametrize(
    ("stack", "length", "stack_element", "rolling_option", "expected"),
    [
        (
            ["01", "02", "03", "04", "aabbccddeeff"],
            6,
            StackBaseElement(0),
            True,
            ["01", "02", "03", "04", "ffeeddccbbaa"],
        ),
        (["01", "02", "aabbccddee", "03", "04"], 5, StackBaseElement(2), True, ["01", "02", "03", "04", "eeddccbbaa"]),
        (
            ["aabbccdd", "01", "02", "03", "04"],
            4,
            StackBaseElement(-1),
            False,
            ["aabbccdd", "01", "02", "03", "04", "ddccbbaa"],
        ),
    ],
)
def test_reverse_endianness(stack, length, stack_element, rolling_option, expected):
    unlock = Script()
    for el in stack:
        unlock.append_pushdata(bytes.fromhex(el))

    lock = reverse_endianness(length, stack_element, rolling_option)
    for ix, el in enumerate(expected[::-1]):
        lock.append_pushdata(bytes.fromhex(el))
        lock += Script.parse_string("OP_EQUAL" if ix == len(expected) - 1 else "OP_EQUALVERIFY")

    context = Context(unlock + lock)
    assert context.evaluate()
    assert len(context.get_stack()) == 1

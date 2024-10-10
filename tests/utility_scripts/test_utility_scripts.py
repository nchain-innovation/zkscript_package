import pytest
from tx_engine import Context, Script

from src.zkscript.util.utility_scripts import mod, nums_to_script, pick, roll, verify_constant


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
    ],
)
def test_pick(position, n_elements, stack, expected):
    unlock = nums_to_script(stack)

    lock = pick(position, n_elements)
    lock += generate_verify(expected)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0


@pytest.mark.parametrize(
    ("is_from_alt", "is_mod_on_top", "is_constant_reused", "is_positive", "stack", "expected"),
    [
        (False, False, False, False, [5, -7], [-2]),
        (False, False, False, True, [5, -7], [3]),
        (False, False, True, False, [5, -7], [5, -2]),
        (False, False, True, True, [5, -7], [5, 3]),
        (False, True, False, False, [-7, 5], [-2]),
        (False, True, False, True, [-7, 5], [3]),
        (False, True, True, False, [-7, 5], [5, -2]),
        (False, True, True, True, [-7, 5], [5, 3]),
        (True, False, False, False, [-7, 3, 5], [3, -2]),
        (True, False, False, True, [-7, 3, 5], [3, 3]),
        (True, False, True, False, [-7, 3, 5], [3, 5, -2]),
        (True, False, True, True, [-7, 3, 5], [3, 5, 3]),
        (True, True, False, False, [5, 3, -7], [3, -2]),
        (True, True, False, True, [5, 3, -7], [3, 3]),
        (True, True, True, False, [5, 3, -7], [3, 5, -2]),
        (True, True, True, True, [5, 3, -7], [3, 5, 3]),
        (False, False, False, False, [13, -17], [-4]),
        (False, False, False, True, [13, -17], [9]),
        (False, False, True, False, [13, -17], [13, -4]),
        (False, False, True, True, [13, -17], [13, 9]),
        (False, True, False, False, [-17, 13], [-4]),
        (False, True, False, True, [-17, 13], [9]),
        (False, True, True, False, [-17, 13], [13, -4]),
        (False, True, True, True, [-17, 13], [13, 9]),
    ],
)
def test_mod(is_from_alt, is_mod_on_top, is_positive, is_constant_reused, stack, expected):
    unlock = nums_to_script(stack)
    lock = Script()
    if is_from_alt:
        lock += Script.parse_string("OP_TOALTSTACK")

    lock += mod(
        is_from_alt=is_from_alt,
        is_mod_on_top=is_mod_on_top,
        is_positive=is_positive,
        is_constant_reused=is_constant_reused,
    )
    lock += generate_verify(expected)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0


@pytest.mark.parametrize(
    ("n", "check_constant", "stack", "expected"),
    [
        (1, True, [1, 0, 0], [1, 0, 0]),
        (10, False, [1, 0, 0], [1, 0, 0]),
        (100, True, [100, 0, 0], [100, 0, 0]),
        (1000, True, [1000] + [0] * 1000, [1000] + [0] * 1000),
    ],
)
def test_verify_constant(n, check_constant, stack, expected):
    unlock = nums_to_script(stack)

    lock = verify_constant(n=n, check_constant=check_constant)
    lock += generate_verify(expected)

    context = Context(script=unlock + lock)

    assert context.evaluate()
    assert len(context.get_altstack()) == 0
